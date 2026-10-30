"""doc2md 解析适配器：调用上游解析、判断能力、把产物交给 ParseArtifact 仓。

边界（都是源码事实，不是推断）
------------------------------
1. doc2md 的产物目录由 `app/core/parsed_paths.py` 决定：
   `parsed/by_hash/<aa>/<bb>/<sha256>/{parsed_text.md, parsed_metadata.json,
   parse_manifest.json, document_ir.json, rendered.md, ir_source/}`。
   其中 `rendered.md` 是派生展示轨，**不是**证据基准，因此不进产物清单（由 store 排除）。
2. 截至 doc2md `d9e4f98`，`parse-markitdown` 只写三件套
   （`markitdown_parser.py:437-483`），`parse-mineru-pdf` 额外写 `ir_source/`
   （`mineru_pdf_parser.py:624`），但**两条路径都没有调用
   `services/document_ir_builder.py`，也就是都不产出 `document_ir.json`**。
3. 而 V2 `ParseArtifact` 合同要求 `ir_schema=document-ir/1.0` 且四件套齐备。
   所以本适配器**不**把 text-only 产物硬塞成 ParseArtifact，而是显式抛
   `UPSTREAM_IR_MISSING`，把"上游缺 IR 出口"记成可诊断的阻塞，而不是静默降级。

本模块不认识 Nebula/ES/Milvus，也不解析原件；解析只在 doc2md 内部发生一次。
"""

import hashlib
import os
import subprocess
from pathlib import Path

from parse_artifact import store

DOC2MD_PARSED_LAYOUT = ("parsed_text.md", "parsed_metadata.json", "parse_manifest.json",
                        "document_ir.json")


class AdapterFailed(RuntimeError):
    """上游命令执行失败（非零退出、超时、缺可执行入口）。"""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class UpstreamContractGap(RuntimeError):
    """上游产物不满足 V2 产物合同（当前主要是缺 Document IR）。"""

    def __init__(self, code, detail="", evidence=None):
        self.code = code
        self.detail = detail
        self.evidence = evidence or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def locate_artifact(parsed_root, content_uid):
    """按 doc2md 的目录约定定位一次解析产物目录。"""
    uid = str(content_uid).lower()
    if len(uid) != 64 or any(c not in "0123456789abcdef" for c in uid):
        raise AdapterFailed("BAD_CONTENT_UID", str(content_uid))
    return Path(parsed_root) / "by_hash" / uid[:2] / uid[2:4] / uid


def capability_report(artifact_dir):
    """如实报告上游实际给了什么能力，不按期望值填写。"""
    root = Path(artifact_dir)
    has = {name: (root / name).is_file() for name in DOC2MD_PARSED_LAYOUT}
    metadata_has_uid = False
    metadata = root / "parsed_metadata.json"
    if metadata.is_file():
        import json
        try:
            metadata_has_uid = bool(json.loads(metadata.read_text(encoding="utf-8")).get("content_uid"))
        except Exception:  # noqa: BLE001
            metadata_has_uid = False
    return {
        "artifact_dir": str(root),
        "parsed_text": has["parsed_text.md"],
        "parsed_metadata": has["parsed_metadata.json"],
        "parse_manifest": has["parse_manifest.json"],
        "document_ir": has["document_ir.json"],
        "ir_source_dir": (root / "ir_source").is_dir(),
        "rendered_md": (root / "rendered.md").is_file(),
        "metadata_has_content_uid": metadata_has_uid,
        "v2_artifact_ready": all(has.values()) and metadata_has_uid,
    }


def producer_inputs(source_revision, runtime_lock=None, config=None, model_fingerprints=None):
    """构造 ParseArtifact.producer 的输入指纹；hash 一律对实际文件算，不填占位值。"""
    inputs = {"source_revision": source_revision,
              "model_fingerprints": list(model_fingerprints or [])}
    if runtime_lock is not None:
        inputs["runtime_lock_hash"] = _sha256_file(runtime_lock)
    if config is not None:
        inputs["config_hash"] = _sha256_file(config)
    return inputs


class Doc2mdAdapter:
    """一次解析 = 一条命令 + 一个产物目录 + 一次快照提交。

    command 是模板列表，支持 `{content_uid}` / `{config}` 占位；由调用方给出，
    因为不同部署的入口不同（CLI / 服务 / 容器），但**产物布局与合同判定是同一套**。
    """

    def __init__(self, parsed_root, command, cwd=None, env_extra=None, timeout=1800):
        self.parsed_root = Path(parsed_root)
        self.command = list(command)
        self.cwd = cwd
        self.env_extra = dict(env_extra or {})
        self.timeout = timeout

    def render_command(self, content_uid, config=None):
        return [str(part).replace("{content_uid}", str(content_uid))
                       .replace("{config}", "" if config is None else str(config))
                for part in self.command]

    def run(self, content_uid, config=None):
        argv = self.render_command(content_uid, config=config)
        env = dict(os.environ)
        env.update({k: str(v) for k, v in self.env_extra.items()})
        try:
            proc = subprocess.run(argv, cwd=self.cwd, env=env, timeout=self.timeout,
                                  capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise AdapterFailed("DOC2MD_ENTRY_MISSING", f"{argv[0]}: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise AdapterFailed("DOC2MD_TIMEOUT", f"{self.timeout}s {argv}") from exc
        if proc.returncode != 0:
            tail = ((proc.stderr or "") + (proc.stdout or "")).strip().splitlines()[-6:]
            raise AdapterFailed("DOC2MD_EXIT_NONZERO",
                                f"exit={proc.returncode} argv={argv} tail={' | '.join(tail)}")
        return proc

    def parse_to_artifact(self, content_uid, store_root, source_revision,
                          config=None, runtime_lock=None, model_fingerprints=None,
                          artifact_id=None):
        """跑上游 → 判断能力 → 交 ParseArtifact 仓。返回 (artifact, target)。"""
        self.run(content_uid, config=config)
        artifact_dir = locate_artifact(self.parsed_root, content_uid)
        if not artifact_dir.is_dir():
            raise AdapterFailed("ARTIFACT_DIR_MISSING", str(artifact_dir))
        report = capability_report(artifact_dir)
        if not report["document_ir"] or not report["metadata_has_content_uid"]:
            # 不降级、不补造 IR：把上游缺口当作阻塞上报（设计 §4.4 的能力探测要求）
            raise UpstreamContractGap(
                "UPSTREAM_IR_MISSING",
                "doc2md 产物不满足 V2 ParseArtifact（需要 document_ir.json 与 metadata.content_uid）；"
                "text-only 产物不得标作结构化完整",
                evidence=report,
            )
        inputs = producer_inputs(source_revision, runtime_lock=runtime_lock, config=config,
                                 model_fingerprints=model_fingerprints)
        return store.commit(artifact_dir, store_root, inputs, artifact_id=artifact_id)
