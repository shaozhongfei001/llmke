#!/usr/bin/env python
"""`use-mineru` 开关真跑：开 → 扫描件走 MinerU 出正文；关 → 走原解析器（几乎没正文）。

为什么要跑这个而不是只改配置：
- 开关读的是 nacos 里的 `use-mineru`，服务里还有 `bypass` 兜底。只看代码无法确认
  "开了真的走 MinerU" 和 "关了不会崩"；
- MinerU 走的是 MinIO 拉文件（`MinioFile`），本地路径会被当成 bucket `/` 直接报错——
  这个坑只有真跑才会遇到，所以演练必须把文件先传进 MinIO。

用法：
  # 主流程（发布两个 data-id → 上传样本 → 各跑一次 → 断言）
  python scripts/v2_switch_drill.py --pdf <local.pdf> --out /tmp/switch.json
  # 内部 worker（由主流程以子进程调用，配置靠环境变量隔离）
  python scripts/v2_switch_drill.py --worker --pdf <minio路径>
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE = os.path.join(HERE, "services/rag-alg/alg_doc_parse_service")
KEY_TEXT = "授信审批意见通知书"


# ---------------------------------------------------------------- nacos
def nacos_base():
    return os.environ.get("NACOS_SERVER_ADDRESS", "http://127.0.0.1:18848").rstrip("/")


def fetch_config(data_id, group="DEFAULT_GROUP"):
    url = (f"{nacos_base()}/nacos/v1/cs/configs?"
           + urllib.parse.urlencode({"dataId": data_id, "group": group, "tenant": ""}))
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def publish_config(data_id, content, group="DEFAULT_GROUP"):
    body = urllib.parse.urlencode({"dataId": data_id, "group": group,
                                   "content": content, "type": "yaml"}).encode()
    req = urllib.request.Request(f"{nacos_base()}/nacos/v1/cs/configs", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8")


def flip_switch(content, value):
    """只改 use-mineru 这一行，其余原样回写（不要重排配置，人工 diff 才看得懂）。"""
    out, changed = [], False
    for line in content.splitlines():
        if line.startswith("use-mineru:"):
            out.append(f"use-mineru: {'true' if value else 'false'}")
            changed = True
        else:
            out.append(line)
    if not changed:
        raise SystemExit("配置里找不到 use-mineru，拒绝猜测")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- minio
def minio_client():
    from minio import Minio

    java = fetch_config(os.environ.get("NACOS_JAVA_DATA_ID", "alg_doc_parse_java_common"))
    import yaml

    cfg = yaml.safe_load(java)
    raw = cfg["minio"]["uri"] if "minio" in cfg else cfg["java-common"]["minio"]["uri"]
    access = (cfg.get("minio") or cfg["java-common"]["minio"])["access-key"]
    secret = (cfg.get("minio") or cfg["java-common"]["minio"])["secret-key"]
    host_ip = cfg.get("server", {}).get("host-ip", "127.0.0.1")
    raw = raw.replace("${server.host-ip}", host_ip)
    secure = raw.startswith("https://")
    endpoint = raw.split("://", 1)[1]
    return Minio(endpoint, access_key=access, secret_key=secret, secure=secure)


def ensure_object(bucket, key, path):
    client = minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    with open(path, "rb") as fh:
        data = fh.read()
    import io

    client.put_object(bucket, key, io.BytesIO(data), length=len(data))
    return f"{bucket}/{key}"


# ---------------------------------------------------------------- worker
def run_worker(pdf):
    """在子进程里跑一次真实 load_files，输出结构化结果（配置由环境变量决定）。"""
    sys.path.insert(0, SERVICE)
    os.chdir(SERVICE)
    from loguru import logger

    # 平台日志默认 enqueue=True，队列 sink 在 magic_pdf 的多进程里会被 pickle →
    # "cannot pickle '_io.TextIOWrapper'"。必须先 import log 让平台配好，再整体换成可丢弃 sink。
    import log  # noqa: F401  （顺序不能反：晚 import 会把队列 sink 又装回来）
    logger.remove()
    events = []
    # 收一份日志到内存：否则"回退有没有真的发生"只能靠猜（stderr sink 会被 pickle 炸）
    logger.add(lambda m: events.append(str(m).strip()), level="INFO")

    # MinerUParser 里 `file_name + request_id.get()` 直接拼字符串：
    # 没有请求上下文时 get() 返回 None → TypeError。真实服务由中间件设置，
    # 脚本里必须自己设，否则会看到"开了 MinerU 却立刻失败"的假象。
    from log import request_id
    request_id.set(f"switch-{os.getpid()}")

    from server.api_param import FileParams, ModelInfo, ParseParams
    from server.loader import load_files

    params = ParseParams(
        knowledge_base_name="v2probe",
        files=[FileParams(file_path=pdf, file_id=999001)],
        file_type="naive", need_chunk=False, save_txt=False,
        model_info=ModelInfo(model_id="qwen2.5-7b-instruct", url="http://127.0.0.1:18092/v1"),
        embedding_model_info=ModelInfo(model_id="text-embedding-bge-m3",
                                       url="http://127.0.0.1:18090/v1"),
        multi_model_info=ModelInfo(model_id="qwen2.5-vl", url="http://127.0.0.1:18093/v1"),
    )
    docs, error = [], None
    try:
        for item in load_files(params, multi_modal=False, need_image_boxes=False):
            for doc in (item.documents or []):
                # ParsedText 是 langchain Document：正文在 page_content，`.text` 不存在。
                # 我第一版读的是 getattr(doc,'text','')，于是"解析成功"看起来是 0 字符——
                # 这是量尺错了，不是解析器错了。
                text = (getattr(doc, "page_content", "") or getattr(doc, "text", "") or "")
                if text:
                    docs.append(text)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    text = "\n".join(docs)
    print("__RESULT__" + json.dumps({
        "chars": len(text), "docs": len(docs), "error": error,
        "hit": KEY_TEXT in text, "sample": text[:80].replace("\n", " "),
        "events": [e[-120:] for e in events
                   if any(k in e for k in ("使用minerU", "使用parser", "解析失败", "外部解析器"))][:6],
    }, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- main
def run_variant(base_config, name, enabled, pdf, py, extra_env):
    data_id = f"alg_doc_config_py_{name}"
    publish_config(data_id, flip_switch(base_config, enabled))
    env = {**os.environ, **extra_env,
           "NACOS_SERVER_ADDRESS": nacos_base(), "NACOS_NAMESPACE": "",
           "NACOS_DATA_ID": data_id, "DATA_ID": data_id, "NACOS_GROUP": "DEFAULT_GROUP",
           "PYTHONPATH": SERVICE}
    proc = subprocess.run([py, os.path.abspath(__file__), "--worker", "--pdf", pdf],
                          capture_output=True, text=True, timeout=2400, env=env, cwd=SERVICE)
    payload = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__RESULT__"):
            payload = json.loads(line[len("__RESULT__"):])
    if payload is None:
        payload = {"error": (proc.stderr or "")[-400:], "chars": 0, "docs": 0,
                   "hit": False, "sample": ""}
    payload["data_id"] = data_id
    payload["use_mineru"] = enabled
    payload["exit"] = proc.returncode
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--base-data-id", default="alg_doc_config_py_v2test")
    ap.add_argument("--bucket", default="v2probe")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.worker:
        return run_worker(args.pdf)

    base = fetch_config(args.base_data_id)
    key = os.path.basename(args.pdf)
    minio_path = ensure_object(args.bucket, key, os.path.abspath(args.pdf))

    mineru_env = {
        "MINERU_TOOLS_CONFIG_JSON": os.environ.get(
            "MINERU_TOOLS_CONFIG_JSON", os.path.expanduser("~/mineru/magic-pdf.json")),
        "HF_HUB_OFFLINE": "1", "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1",
    }
    on = run_variant(base, "v2switch_on", True, minio_path, args.python, mineru_env)
    off = run_variant(base, "v2switch_off", False, minio_path, args.python, {})
    # 开但 MinerU 坏：走 loader 的 bypass 兜底，必须不崩、不静默返回"成功但没内容"之外的东西
    broken_env = {**mineru_env, "MINERU_TOOLS_CONFIG_JSON": "/nonexistent/magic-pdf.json"}
    broken = run_variant(base, "v2switch_broken", True, minio_path, args.python, broken_env)

    problems = []
    if not on.get("hit"):
        problems.append(f"开开关后没抽到关键中文（chars={on.get('chars')}, err={on.get('error')}）")
    if off.get("hit"):
        problems.append("关开关后仍抽到关键中文，说明开关没生效")
    if off.get("error"):
        problems.append(f"关开关时原解析器报错：{off['error']}")
    if broken.get("error"):
        problems.append(f"开开关但 MinerU 不可用时没有走 bypass 兜底：{broken['error']}")
    if not any("外部解析器解析失败" in e for e in (broken.get("events") or [])):
        problems.append("MinerU 配置不可用时没看到 bypass 回退日志（可能静默失败了）")
    if not any("使用parser" in e for e in (broken.get("events") or [])):
        problems.append("bypass 之后没有落到自建解析（回退链断了）")

    report = {"status": "OK" if not problems else "FAIL", "pdf": minio_path,
              "on": on, "off": off, "broken": broken, "problems": problems}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"status": report["status"], "on_chars": on.get("chars"),
                      "off_chars": off.get("chars"), "broken_chars": broken.get("chars"),
                      "problems": problems}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
