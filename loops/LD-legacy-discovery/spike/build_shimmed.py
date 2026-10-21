#!/usr/bin/env python3
"""生成「已切断服务层耦合」的 deepdoc 副本，用于行为回放对比。

做什么：
  1. 复制原模块的 `deepdoc/` 与 `log.py` 到输出目录（**不修改原仓**）
  2. 把 `from server.*` 的 4 类耦合改成 `from _shims.*`
  3. 把 `deepdoc/parser/__init__.py` 从「全量导入 14 个解析器」改为按需导入
  4. 生成 `_shims/`：配置、模型引用、进度上报、运行时工具、异常类

为什么 shim 要抄原实现：`compile_extension_regex_ignore_case` / `run_in_thread_pool` / `create_uuid`
是纯函数，必须逐字复制，否则「行为一致」的结论会被 shim 自身的差异污染。
`load_local_ocr` 涉及 ONNX 模型，本次回放不覆盖 OCR，故显式抛错而不是假装可用。

用法：
  python3 build_shimmed.py --src <alg_doc_parse_service> --out /tmp/llmke-spike/shimmed
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

REWRITES = [
    (re.compile(r"from server\.nacos_utils import DocParseConfig"),
     "from _shims.config import DocParseConfig"),
    (re.compile(r"from server\.api_param import ModelInfo"),
     "from _shims.model import ModelInfo"),
    (re.compile(r"from server\.process_reporter import ProcessReporter"),
     "from _shims.progress import ProcessReporter"),
    (re.compile(r"from server\.utils import ([^\n(]+)"),
     r"from _shims.runtime import \1"),
    (re.compile(r"from server\.exception\.custom_exception import \(([^)]*)\)",
                re.S),
     r"from _shims.errors import (\1)"),
]

LAZY_INIT = '''"""按需导入的解析器注册表。

原实现的 `__init__.py` 一次性 import 14 个解析器，等于把 magic_pdf / onnxruntime /
阿里云 SDK 全部变成导入期硬依赖（实测：仅 import 包就报 ModuleNotFoundError）。
这里改为惰性：只有真正用到某个解析器时才导入它。
"""

_LAZY = {
    "AliParser": ("ali_parser", "AliParser"),
    "CSVParser": ("csv_parser", "Parser"),
    "DOCParser": ("doc_parser", "Parser"),
    "DOCXParser": ("docx_parser", "Parser"),
    "ExcelParser": ("excel_parser", "Parser"),
    "FudanParser": ("fudan_parser", "FudanParser"),
    "HTMLParser": ("html_parser", "Parser"),
    "ImageParser": ("image_parser", "Parser"),
    "MinerUParser": ("mineru_parser", "MinerUParser"),
    "PDFParser": ("pdf_parser", "Parser"),
    "PDFPlainParser": ("pdf_parser", "PlainParser"),
    "PPTParser": ("ppt_parser", "Parser"),
    "TextInParser": ("text_in_parser", "TextInParser"),
    "TXTParser": ("txt_parser", "Parser"),
    "WPSParser": ("wps_parser", "Parser"),
}


def __getattr__(name):
    if name not in _LAZY:
        raise AttributeError(name)
    import importlib
    mod_name, attr = _LAZY[name]
    mod = importlib.import_module("." + mod_name, __name__)
    return getattr(mod, attr)


__all__ = list(_LAZY)
'''

SHIMS = {
    "config.py": '''"""DocParseConfig 的静态替身：原实现从 Nacos 拉配置（含内网地址），这里改为本地字典。"""

DEFAULTS = {
    "doc-parse": {
        "chunk_size": 500,
        "overlap_size": 50,
        "min_chunk_size": 10,
        "paragraph_separator": "\\n",
        "delimiter": "\\n",
        "layout_recognize": "DeepDOC",
        "filename_embd_weight": 0.1,
    },
    "alg-common": {
        "online_embedding_model": {"max_token": 8192, "max_token_delta": 512},
    },
}


class DocParseConfig:
    _instance = None

    def __init__(self, configs=None):
        self.configs = dict(DEFAULTS)
        if configs:
            self.configs.update(configs)

    @property
    def config(self):
        return self.configs["doc-parse"]

    @classmethod
    def create_client(cls, *args, **kwargs):
        raise RuntimeError("nacos 已在新边界中移除；请用静态配置注入")
''',
    "model.py": '''"""ModelInfo 替身：只保留字段，不建立任何连接。"""
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    model_id: str = Field(description="openai api 中的 model")
    url: str = Field(description="模型 url")
    key: str | None = Field(default=None, description="api key")
''',
    "progress.py": '''"""ProcessReporter 替身：默认不落库，只记录调用次数，便于断言「耦合被切断了」。"""


class _Dao:
    def __init__(self):
        self.inserts = 0

    def insert(self, *args, **kwargs):
        self.inserts += 1


class ProcessReporter:
    def __init__(self, *args, **kwargs):
        self.dao = _Dao()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
''',
    "runtime.py": '''"""原 server/utils.py 中纯函数的逐字副本 + OCR 的显式不可用。"""
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Generator


class _NoOcr:
    """占位 OCR：构造成功（原实现在 __init__ 里就会加载模型），一旦真正调用即显式报错。"""

    def __call__(self, *args, **kwargs):
        raise RuntimeError("OCR 未纳入本次回放：需要 ONNX 模型与会话池，属于显式缺口，不静默降级")

    def __getitem__(self, key):
        # 原实现：load_local_ocr()['ocr']
        return self

    def __getattr__(self, name):
        raise RuntimeError(f"OCR 能力 {name} 未纳入本次回放")


def load_local_ocr(device="cpu"):
    return _NoOcr()


def run_in_thread_pool(func: Callable, params: list[dict] | None = None,
                       stable_order=False, max_workers=None) -> Generator:
    if params is None:
        params = []
    tasks = []
    if max_workers is None or max_workers > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for kwargs in params:
                tasks.append(pool.submit(func, **kwargs))
            if not stable_order:
                for obj in as_completed(tasks):
                    yield obj.result()
            else:
                for task in tasks:
                    yield task.result()
    else:
        for kwargs in params:
            yield func(**kwargs)


def create_uuid():
    pk_value = uuid.uuid4().int & ((1 << 63) - 1)
    if pk_value > 9223372036854775807:
        pk_value = pk_value - (1 << 64)
    return pk_value


def compile_extension_regex_ignore_case(extensions: list[str]) -> list[re.Pattern[str]]:
    return [re.compile("^[\\s\\S]*" + re.escape(e) + "$", re.IGNORECASE) for e in extensions]
''',
    "errors.py": '''"""异常类替身：只保留类型与消息，不依赖 FastAPI。"""


class ApiError(Exception):
    def __init__(self, message="", code=None):
        super().__init__(message)
        self.message = message
        self.code = code


class UnknownError(ApiError):
    pass


class FileParseFailedError(ApiError):
    pass


class ModelRequestInternalError(ApiError):
    pass


class MineruServiceUnavailableError(ApiError):
    pass


class MineruResourceInsufficientError(ApiError):
    pass

class MineruRequestTimeoutError(ApiError):
    pass


class ModelTokenExceedError(ApiError):
    pass
''',
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True, help="原 alg_doc_parse_service 根")
    ap.add_argument("--out", type=Path, required=True, help="输出目录")
    ap.add_argument("--no-rewrite", action="store_true",
                    help="只做惰性 __init__，不改 server.* 导入（用于构造对照臂 A）")
    a = ap.parse_args()

    src, out = a.src.resolve(), a.out.resolve()
    if not (src / "deepdoc").is_dir():
        raise SystemExit(f"not a source root: {src}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    shutil.copytree(src / "deepdoc", out / "deepdoc")
    shutil.copy2(src / "log.py", out / "log.py")

    changed = []
    if not a.no_rewrite:
        for p in sorted((out / "deepdoc").rglob("*.py")):
            text = p.read_text(encoding="utf-8")
            original = text
            for pat, rep in REWRITES:
                text = pat.sub(rep, text)
            if text != original:
                p.write_text(text, encoding="utf-8")
                changed.append(p.relative_to(out).as_posix())

    (out / "deepdoc" / "parser" / "__init__.py").write_text(LAZY_INIT, encoding="utf-8")

    shims = out / "_shims"
    shims.mkdir()
    (shims / "__init__.py").write_text("", encoding="utf-8")
    for name, body in SHIMS.items():
        (shims / name).write_text(body, encoding="utf-8")

    print(f"shimmed -> {out}")
    print(f"rewritten files: {len(changed)}")
    for c in changed:
        print("  ", c)
    print(f"lazy parser/__init__ replaced; shims: {', '.join(sorted(SHIMS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
