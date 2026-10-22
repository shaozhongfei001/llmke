"""W-05b：进程入口自钉解释器（只依赖标准库，必须最先被导入）。

R-02 的根因不是 Makefile 单点：整条链**第一个** `python3` 来自 PATH。
门禁 argv 里的 `python3` 已由 loop_guard 换成 `sys.executable`，因此只要入口用对解释器，
spawn 出去的 make / pytest / 门禁命令就都对。

优先级：LLMKE_PYTHON → <repo>/.venv/bin/python3 → 保持现状（不改变任何门禁语义）。
为什么必须"先于重型导入"：系统 python3 可能连 yaml 都没有，等到 main() 里再钉就已经太晚。
"""
import os
import sys
from pathlib import Path


def _pin() -> None:
    if os.environ.get("LLMKE_PYTHON_REEXEC") == "1":
        return
    root = Path(__file__).resolve().parents[1]
    want = os.environ.get("LLMKE_PYTHON")
    if not want:
        cand = root / ".venv" / "bin" / "python3"
        want = str(cand) if cand.is_file() else None
    if not want or not os.access(want, os.X_OK):
        return
    if os.path.realpath(want) == os.path.realpath(sys.executable):
        return
    env = dict(os.environ)
    env["LLMKE_PYTHON_REEXEC"] = "1"
    env["LLMKE_PYTHON"] = want
    env["PATH"] = str(Path(want).parent) + os.pathsep + env.get("PATH", "")
    os.execve(want, [want] + sys.argv, env)


_pin()
