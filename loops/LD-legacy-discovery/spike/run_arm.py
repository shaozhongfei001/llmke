#!/usr/bin/env python3
"""在干净进程里跑一个「臂」（arm），把解析结果写成 JSON。

臂 A：原始字节 + 用 sys.modules 注入假的 `server.*`（等价桩）
臂 B：已完成 server→_shims 改写的副本

两臂共同点：都注入同一套第三方桩（未安装的重依赖），因此差异只来自「耦合切法」。
缺依赖采用**显式 stub finder**，并记录被请求过的模块名，用于量化导入期耦合。

用法：
  python3 run_arm.py --arm A --src-root <alg_doc_parse_service> --shimmed <dir> \
      --sample <file> --out <json>
"""
from __future__ import annotations

import argparse
import importlib
import importlib.abc
import importlib.util
import json
import sys
import time
import types
from pathlib import Path

# 本次回放不覆盖的第三方依赖（PDF/OCR/向量/云 SDK），按需打桩
BLOCK = {
    "magic_pdf", "onnxruntime", "xgboost", "datrie", "hanziconv", "nltk", "jieba",
    "alibabacloud_credentials", "alibabacloud_tea_openapi", "alibabacloud_tea_util",
    "minio", "nacos", "pymysql", "fastapi", "fastapi.responses", "httpx", "openpyxl",
    "xlrd", "pandas", "uvicorn", "gunicorn", "tqdm", "docx2python", "modelscope",
    "huggingface_hub", "modelscope_hub", "torch", "transformers", "cv2", "fitz",
    "pyclipper", "shapely", "pypdf", "camelot", "tabula",
}

REQUESTED: list[str] = []


class _DummyMeta(type):
    def __getattr__(cls, name):
        return _Dummy

    def __iter__(cls):
        return iter(())


class _Dummy(metaclass=_DummyMeta):
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Dummy()

    def __getattr__(self, name):
        return _Dummy()

    def __iter__(self):
        return iter(())


class _DummyModule(types.ModuleType):
    # 必须有 __path__：否则导入 `pkg.sub` 时 PathFinder 会去迭代父包的 __path__，
    # 而 __getattr__ 返回的是类对象 → "TypeError: 'type' object is not iterable"
    __path__ = []

    def __getattr__(self, name):
        return _Dummy


class _StubLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return _DummyModule(spec.name)

    def exec_module(self, module):
        return None


class _StubFinder(importlib.abc.MetaPathFinder):
    """兜底打桩：只在真实 import 失败时才被调用（挂到 sys.meta_path 末尾）。

    这样「需要桩的模块名」就等于「该代码路径真正缺的外部依赖」，
    同时也是导入期耦合的量化指标。所有桩名都会写进结果，便于审计，不是静默忽略。
    """

    def find_spec(self, fullname, path=None, target=None):
        top = fullname.split(".")[0]
        if top in ("_shims", "deepdoc", "server", "log"):
            return None
        # 只对**显式列出**的重依赖打桩：放开成「任何缺失模块」会掩盖真实缺失，
        # 也会让 bs4/zstd 之类在导入期访问桩属性，得到与真实行为无关的报错。
        if top in BLOCK or top.startswith(("alibabacloud", "magic_pdf")):
            if fullname not in REQUESTED:
                REQUESTED.append(fullname)
            return importlib.util.spec_from_loader(fullname, _StubLoader())
        return None


def install_server_stub(shimmed: Path) -> None:
    """把 server.* 映射到 _shims（与臂 B 使用同一套实现，隔离变量）。

    注意：只能 append，不能 insert(0)——否则 shimmed 目录会抢在原始目录之前被
    解析成 `deepdoc`，臂 A 就悄悄变成了臂 B（本脚本初版犯过这个错）。
    """
    sys.path.append(str(shimmed))
    from _shims import config, errors, model, progress, runtime  # noqa: E402

    server = types.ModuleType("server")
    server.__path__ = []  # 标记为包

    nacos_utils = types.ModuleType("server.nacos_utils")
    nacos_utils.DocParseConfig = config.DocParseConfig

    api_param = types.ModuleType("server.api_param")
    api_param.ModelInfo = model.ModelInfo

    utils = types.ModuleType("server.utils")
    utils.load_local_ocr = runtime.load_local_ocr
    utils.run_in_thread_pool = runtime.run_in_thread_pool
    utils.create_uuid = runtime.create_uuid
    utils.compile_extension_regex_ignore_case = runtime.compile_extension_regex_ignore_case

    process_reporter = types.ModuleType("server.process_reporter")
    process_reporter.ProcessReporter = progress.ProcessReporter

    exception = types.ModuleType("server.exception")
    exception.__path__ = []
    custom_exception = types.ModuleType("server.exception.custom_exception")
    for name in dir(errors):
        if name.startswith("_") or name == "ApiError":
            continue
        setattr(custom_exception, name, getattr(errors, name))

    sys.modules.update({
        "server": server,
        "server.nacos_utils": nacos_utils,
        "server.api_param": api_param,
        "server.utils": utils,
        "server.process_reporter": process_reporter,
        "server.exception": exception,
        "server.exception.custom_exception": custom_exception,
    })


def norm(obj):
    if hasattr(obj, "model_dump"):
        return norm(obj.model_dump())
    if isinstance(obj, dict):
        return {str(k): norm(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [norm(v) for v in obj]
    if isinstance(obj, set):
        return sorted(norm(v) for v in obj)
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


META_KEYS = ["type", "position", "page_number", "page_size", "offset",
             "need_filtered", "title_path", "chunk_index", "table_name", "base64"]


def summarize(blocks):
    out = []
    for b in blocks:
        d = norm(b)
        meta = d.get("metadata") or {}
        item = {
            "page_content": d.get("page_content"),
            "type": meta.get("type"),
            "meta": {k: meta.get(k) for k in META_KEYS if k in meta},
        }
        if item["type"] == "image" or item["type"] == "table":
            item["page_content_head"] = (item["page_content"] or "")[:120]
        out.append(item)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["A", "B"], required=True)
    ap.add_argument("--src-root", type=Path, required=True)
    ap.add_argument("--shimmed", type=Path, required=True)
    ap.add_argument("--sample", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    sys.meta_path.append(_StubFinder())
    if a.arm == "A":
        sys.path.insert(0, str(a.src_root.resolve()))
        install_server_stub(a.shimmed.resolve())
    else:
        sys.path.insert(0, str(a.shimmed.resolve()))

    suffix = a.sample.suffix.lower()
    target = {".docx": "docx_parser", ".txt": "txt_parser", ".html": "html_parser",
              ".htm": "html_parser", ".md": "txt_parser", ".csv": "csv_parser"}.get(suffix)
    if not target:
        raise SystemExit(f"unsupported sample type: {suffix}")

    started = time.time()
    try:
        from langchain_core.document_loaders import Blob

        mod = importlib.import_module(f"deepdoc.parser.{target}")
        deepdoc_file = getattr(mod, "__file__", "")
        factory = getattr(mod, "Parser")
        # 原实现的 Parser 是工厂：Parser.get_parser() 才返回可调用实例
        instance = factory.get_parser() if hasattr(factory, "get_parser") else factory()
        blocks = list(instance.lazy_parse(Blob.from_path(str(a.sample))))
        result = {"arm": a.arm, "sample": a.sample.name, "ok": True,
                  "deepdoc_file": deepdoc_file,
                  "count": len(blocks), "blocks": summarize(blocks)}
    except Exception as e:  # noqa: BLE001
        result = {"arm": a.arm, "sample": a.sample.name, "ok": False,
                  "error": f"{type(e).__name__}: {e}"}
    result["elapsed_ms"] = int((time.time() - started) * 1000)
    result["stubbed_modules"] = sorted(REQUESTED)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"arm": a.arm, "sample": a.sample.name, "ok": result["ok"],
                      "count": result.get("count"),
                      "stubs": len(REQUESTED)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
