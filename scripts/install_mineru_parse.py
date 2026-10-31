#!/usr/bin/env python3
"""把 MinerU（magic-pdf）装进一个"已经是 parse 依赖"的环境，顺序敏感、可重复执行。

为什么不能一条 `pip install "magic-pdf[core]"`：
- `[core]` 缺 4 个模块级导入依赖（pycocotools / ultralytics / doclayout_yolo / rapid_table），
  缺任一个都在 import 阶段就崩；
- 这些包会把 numpy 顶到 2.x，而 parse 侧的 pandas 是按 numpy 1.x 编的，一升就
  `numpy.dtype size changed` —— 必须每轮装完回锁 numpy；
- torch ≥2.6 默认 `weights_only=True`，doclayout_yolo 的 ckpt 会被拒，需要
  `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`（这里只写进提示，不改用户环境）。

用法：
  scripts/install_mineru_parse.py --python /path/to/venv/bin/python \
      --mineru-config /home/szf/data/dev/models/mineru/magic-pdf.json
"""

import argparse
import json
import os
import subprocess
import sys

# 顺序有讲究：先装上游包，再装它缺的模块级依赖，最后回锁 numpy
STEPS = [
    ["magic-pdf[core]==1.3.12"],
    ["pycocotools"],
    ["ultralytics"],
    ["doclayout-yolo"],
    ["rapid-table"],
    ["dill"],
    ["openai"],
    ["numpy==1.26.4"],          # 每轮装完都必须回锁（见文件头）
]

CHECK_IMPORTS = ["magic_pdf", "pycocotools", "ultralytics", "doclayout_yolo",
                 "rapid_table", "dill", "openai", "numpy", "pandas"]

DEFAULT_CONFIG = {
    "models-dir": "/home/szf/data/dev/models/mineru/models",
    "device-mode": "cpu",
    "layout-config": {"model": "doclayout_yolo"},
    "formula-config": {"mfd_model": "yolo_v8_mfd", "mfr_model": "unimernet_small", "enable": False},
    "table-config": {"model": "rapid_table", "sub_model": "slanet_plus", "enable": False,
                     "max_time": 400},
    "layoutreader-model-dir":
        "/home/szf/data/dev/models/mineru/models/ReadingOrder/layout_reader",
}


def _pip(python, args):
    cmd = [python, "-m", "pip", "install", "-q", "--no-cache-dir"] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stderr or "").strip().splitlines()[-2:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--mineru-config", default="/home/szf/data/dev/models/mineru/magic-pdf.json")
    ap.add_argument("--skip-install", action="store_true", help="只做自检与配置，不装包")
    args = ap.parse_args(argv)

    steps = []
    if not args.skip_install:
        for step in STEPS:
            code, tail = _pip(args.python, step)
            steps.append({"pkg": step[0], "rc": code, "tail": tail})
            if code != 0:
                print(json.dumps({"status": "PIP_FAILED", "steps": steps}, ensure_ascii=False))
                return 1

    # 配置：不存在才写，存在就只报差异，不覆盖运维已调好的值
    cfg_path = args.mineru_config
    cfg_state = "ABSENT"
    if os.path.isfile(cfg_path):
        try:
            cur = json.load(open(cfg_path, encoding="utf-8"))
            cfg_state = "MATCH" if cur == DEFAULT_CONFIG else "DIFFERS"
        except Exception:  # noqa: BLE001
            cfg_state = "UNREADABLE"
    else:
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=1) + "\n")
        cfg_state = "WRITTEN"

    check = subprocess.run(
        [args.python, "-c",
         "import importlib,sys\n"
         f"mods={CHECK_IMPORTS!r}\n"
         "bad=[]\n"
         "for m in mods:\n"
         "    try: importlib.import_module(m)\n"
         "    except Exception as e: bad.append((m,type(e).__name__))\n"
         "import numpy,pandas\n"
         "print(__import__('json').dumps({'bad':bad,'numpy':numpy.__version__,'pandas':pandas.__version__}))"],
        capture_output=True, text=True)
    imports = json.loads(check.stdout.strip() or "{}") if check.returncode == 0 else {
        "bad": [["<interpreter>", "IMPORT_CHECK_FAILED"]], "stderr": check.stderr[-200:]}

    report = {"status": "OK" if not imports.get("bad") else "IMPORTS_BROKEN",
              "python": args.python, "config": {"path": cfg_path, "state": cfg_state},
              "imports": imports, "steps": steps,
              "reminders": ["运行前需设置 MINERU_TOOLS_CONFIG_JSON 指向上面的 config",
                            "torch>=2.6 需 TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1",
                            "离线机需 HF_HUB_OFFLINE=1（权重走本地目录）"]}
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
