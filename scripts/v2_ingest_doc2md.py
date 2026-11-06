#!/usr/bin/env python3
"""一条命令跑完：文件 → doc2md 解析（它自己产四件套）→ 双路消费（搜索 + 按库建图）。

为什么要有这个脚本
------------------
"解析完成自动触发"需要一个可执行的入口：Java 侧已在 `doSuccess` 留了回调
（`FileAppService.v2Ingest` → `18096 /kb/ingest`），但解析链路本身必须**先产出 doc2md 四件套**。
本脚本就是那个"产出四件套并触发消费"的编排入口，可被上传流程 / 批处理 / 人工调用。

它调用的是 doc2md 自己的 CLI（scan → copy-to-vault → route-parsers → parse-markitdown），
四件套由 doc2md 写出，**本脚本不拼任何产物字段**；随后交给 `kb_pipeline.consume()`
把同一份快照投影给搜索、并调 18094 按库建图。

用法
----
    python scripts/v2_ingest_doc2md.py \
        --file /path/to/x.docx --kb kb_9 --file-id 333 \
        --config /path/to/doc2md-app.yaml

前置：
- doc2md 可执行（默认 `python -m app.cli.main`，可用 `--doc2md-python` / `--doc2md-cwd` 覆盖）；
- doc2md 的 MySQL 可达（配置在 `--config` 里）；
- 18094 图服务可达（`--graph-api`，默认 http://127.0.0.1:18094）。
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_DOC2MD_PY = "/home/szf/data/dev/doc2md-toolenv/bin/python"
DEFAULT_DOC2MD_CWD = "/home/szf/data/dev/doc2md/backend"
DEFAULT_MINERU_BIN = "/home/szf/data/dev/mineru-toolenv/bin"
DEFAULT_GRAPH_API = "http://127.0.0.1:18094"
DEFAULT_STORE_ROOT = ".artifacts/artifact-store"


def _run(cmd, cwd, timeout=1800):
    """跑一条 doc2md CLI 命令；非零退出就把尾部输出带出来，不吞。

    PDF 分支要调 magic-pdf，它装在 mineru-toolenv 里，默认不在 PATH 上，
    这里显式补进去（可用 LLMKE_MINERU_BIN 覆盖）。
    """
    env = dict(os.environ)
    mineru_bin = os.environ.get("LLMKE_MINERU_BIN", DEFAULT_MINERU_BIN)
    if Path(mineru_bin).is_dir():
        env["PATH"] = f"{mineru_bin}:{env.get('PATH', '')}"
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=env)
    if proc.returncode != 0:
        tail = ((proc.stderr or "") + (proc.stdout or "")).strip().splitlines()[-8:]
        raise RuntimeError(f"命令失败({proc.returncode}): {' '.join(cmd)}\n" + "\n".join(tail))
    return (proc.stdout or "") + (proc.stderr or "")


def _parsed_dir(parsed_root: Path, sha: str) -> Path:
    return parsed_root / "by_hash" / sha[:2] / sha[2:4] / sha


def _reset_vault_state(config: Path, sha: str, *, doc2md_python: str = DEFAULT_DOC2MD_PY,
                       doc2md_cwd: str = DEFAULT_DOC2MD_CWD) -> None:
    """把 doc2md 库里该内容的 vault 状态重置为 NOT_COPIED。

    为什么要重置：库里 status=COPIED 但实际 vault 目录可能已被清理（换机器 / 清 /tmp），
    此时 copy-to-vault 会直接跳过，parse 就永远拿不到原件。重置后重跑才是真实复制。

    为什么要起子进程：调用方可能是 18096（hipporag 环境，没有 sqlalchemy / doc2md 依赖），
    用 doc2md 自己的解释器执行才不会因缺依赖而静默跳过。
    """
    code = (
        "import sys, json\n"
        "from pathlib import Path\n"
        "from app.core.config import load_config\n"
        "from sqlalchemy import create_engine, text\n"
        f"cfg = load_config(Path({str(config)!r}))\n"
        "m = cfg.mysql\n"
        "e = create_engine(f'mysql+pymysql://{m.username}:{m.password}@{m.host}:{m.port}/{m.database}?charset={m.charset}')\n"
        "with e.begin() as c:\n"
        f"    c.execute(text(\"update kb_file_content set vault_status='NOT_COPIED', vault_path=NULL, "
        f"parse_status=NULL where sha256=:s\"), {{'s': {sha!r}}})\n"
        "print('reset-ok')\n"
    )
    proc = subprocess.run([doc2md_python, "-c", code], cwd=doc2md_cwd,
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        tail = ((proc.stderr or "") + (proc.stdout or "")).strip().splitlines()[-4:]
        raise RuntimeError("重置 vault 状态失败: " + " | ".join(tail))


def ingest_file(file_path: Path, kb: str, file_id, *, config: Path,
                doc2md_python: str = DEFAULT_DOC2MD_PY,
                doc2md_cwd: str = DEFAULT_DOC2MD_CWD,
                store_root: str = DEFAULT_STORE_ROOT,
                graph_api: str = DEFAULT_GRAPH_API,
                graph_root=None, build_graph: bool = True,
                revision: str = "unknown", profile: str = "default_v1",
                timeout: int = 1800) -> dict:
    """文件 → doc2md 四件套 → 双路消费。返回结果字典（含两路统计）。"""
    if not file_path.is_file():
        raise RuntimeError(f"文件不存在：{file_path}")
    if not config.is_file():
        raise RuntimeError(f"doc2md 配置不存在：{config}")

    sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
    cli = [doc2md_python, "-m", "app.cli.main"]
    cfg = ["--config", str(config)]

    # 1) 放进独立目录再 scan：scan 是按目录走的，不能把整个目录都登记进来
    src_dir = Path(tempfile.mkdtemp(prefix="v2-ingest-src-"))
    try:
        shutil.copyfile(file_path, src_dir / file_path.name)
        _run(cli + ["scan", "--path", str(src_dir), "--source-root", kb] + cfg,
             cwd=doc2md_cwd)

        # 2) 库里状态可能是"COPIED 但原件已丢"，重置后才会真正复制
        try:
            _reset_vault_state(config, sha, doc2md_python=doc2md_python, doc2md_cwd=doc2md_cwd)
        except Exception as exc:  # noqa: BLE001 - 重置失败不阻断，copy 会给出真实原因
            print(f"[warn] 重置 vault 状态失败（继续）：{exc}", file=sys.stderr)

        _run(cli + ["copy-to-vault", "--sha256", sha] + cfg, cwd=doc2md_cwd)
        _run(cli + ["route-parsers", "--sha256", sha] + cfg, cwd=doc2md_cwd)

        # PDF 走 MinerU（magic-pdf），其余走 MarkItDown
        # 解析预算可由调用方指定（大文件如 48MB 书籍 600s 必然不够）；
        # magic-pdf 自身的 --timeout 与外层 subprocess 超时都要跟着放大，
        # 外层多留 300s 给 CLI 收尾/写产物，避免"内层跑完、外层先杀"。
        is_pdf = file_path.suffix.lower() == ".pdf"
        if is_pdf:
            parse_budget = max(int(timeout), 600)
            _run(cli + ["parse-mineru-pdf", "--sha256", sha, "--force",
                        "--timeout", str(parse_budget)] + cfg, cwd=doc2md_cwd,
                 timeout=parse_budget + 300)
        else:
            _run(cli + ["parse-markitdown", "--sha256", sha] + cfg, cwd=doc2md_cwd)
    finally:
        shutil.rmtree(src_dir, ignore_errors=True)

    # 3) 定位 doc2md 自己写出的产物
    sys.path.insert(0, str(Path(DEFAULT_DOC2MD_CWD)))
    from app.core.config import load_config  # noqa: E402

    parsed_root = Path(load_config(config).storage.parsed_root)
    doc2md_dir = _parsed_dir(parsed_root, sha)

    # doc2md 的 MinerU 路径只写三件套 + ir_source/，不写 document_ir.json；
    # 用 doc2md 自己的 build_from_mineru_content_list 补齐（平台侧补口，产物里会被标注）。
    if is_pdf and not (doc2md_dir / "document_ir.json").is_file():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from v2_fill_mineru_ir import fill_mineru_ir  # noqa: E402

        fill_mineru_ir(doc2md_dir, doc2md_cwd=doc2md_cwd)

    missing = [n for n in ("parsed_text.md", "parsed_metadata.json",
                           "parse_manifest.json", "document_ir.json")
               if not (doc2md_dir / n).is_file()]
    if missing:
        raise RuntimeError(f"doc2md 未产出完整四件套，缺：{missing}（目录：{doc2md_dir}）")

    # 4) 双路消费（封快照 → 投影 → 按库建图）
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                           / "services/rag-alg/index_data_service"))
    from ingest_pipeline import kb_pipeline as K  # noqa: E402

    lock = os.environ.get("LLMKE_DOC2MD_LOCK")
    if not (lock and Path(lock).is_file()):
        raise RuntimeError("缺少 LLMKE_DOC2MD_LOCK（doc2md 冻结锁文件），无法证明解析基线")
    producer = {
        "source_revision": revision,
        "parser_profile": profile,
        "runtime_lock_hash": hashlib.sha256(Path(lock).read_bytes()).hexdigest(),
        "config_hash": hashlib.sha256(config.read_bytes()).hexdigest(),
        "model_fingerprints": [],
    }
    # 按库摄取：本次文件并入该库清单后，用该库全部文件重建图谱（避免覆盖历史文件）
    result = K.consume_for_kb(
        doc2md_dir, store_root, kb=kb, file_id=file_id, index_name=kb,
        producer_inputs=producer, file_name=file_path.name,
        file_path=str(file_path), file_size=file_path.stat().st_size,
        source=f"{kb}/{file_path.name}", build_graph=build_graph,
        graph_root=graph_root, graph_api=graph_api, timeout=timeout)
    result["doc2md_dir"] = str(doc2md_dir)
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="doc2md 解析 → 双路消费（搜索 + 按库建图）")
    p.add_argument("--file", required=True, help="待解析文件")
    p.add_argument("--kb", required=True, help="知识库标识（primitiveName，如 kb_9）")
    p.add_argument("--file-id", required=True, help="平台文件 id")
    p.add_argument("--config", required=True, help="doc2md app.yaml 路径")
    p.add_argument("--store-root", default=DEFAULT_STORE_ROOT, help="平台快照仓目录")
    p.add_argument("--graph-api", default=DEFAULT_GRAPH_API)
    p.add_argument("--graph-root", default=None, help="图谱落盘根（默认由 18094 环境变量决定）")
    p.add_argument("--no-graph", action="store_true", help="只做搜索路，不建图")
    p.add_argument("--doc2md-python", default=DEFAULT_DOC2MD_PY)
    p.add_argument("--doc2md-cwd", default=DEFAULT_DOC2MD_CWD)
    p.add_argument("--revision", default=os.environ.get("LLMKE_DOC2MD_REVISION", "unknown"))
    p.add_argument("--profile", default="default_v1")
    p.add_argument("--timeout", type=int, default=1800)
    args = p.parse_args()

    try:
        out = ingest_file(
            Path(args.file), args.kb, args.file_id, config=Path(args.config),
            doc2md_python=args.doc2md_python, doc2md_cwd=args.doc2md_cwd,
            store_root=args.store_root, graph_api=args.graph_api,
            graph_root=args.graph_root, build_graph=not args.no_graph,
            revision=args.revision, profile=args.profile, timeout=args.timeout)
    except Exception as exc:  # noqa: BLE001 - 失败要让人看见原因
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    out["projection"].pop("payloads", None)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
