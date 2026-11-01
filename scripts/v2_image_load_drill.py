#!/usr/bin/env python
"""离线镜像 load 演练：tar 在目标机上到底能不能加载、能不能跑起来、会不会顶掉在用 tag。

上一轮只校验了 tar 的摘要/标签/层，**刻意没 load**——因为怕覆盖在用 tag。
这就留下空白：真到离线机现场，`docker load` 失败或起不来才发现，代价最大。

安全约束（写死在代码里，不靠调用方自觉）：
- 只记录"是否覆盖了已存在的 tag"，**绝不自动 rmi**：旧镜像可能正被容器引用；
- 起容器只用随机宿主端口，并在 finally 里 `docker rm -f`，异常也清理；
- 任何一步失败都返回结构化错误 + 退出码 1，不把异常抛给调用方。
"""

import argparse
import json
import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

SCHEMA = "llmke.image-load-drill.v1"

Runner = Callable[[List[str], float], Tuple[int, str, str]]


def default_runner(cmd: List[str], timeout: float = 300.0) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


def parse_images(text: str) -> Dict[str, str]:
    """`docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}'` → {ref: id}。"""
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and not parts[0].startswith("<none>"):
            out[parts[0]] = parts[1]
    return out


def parse_loaded_ref(load_output: str) -> Optional[str]:
    """从 `Loaded image: redis:7.4.10-alpine` 里取镜像引用。"""
    for line in (load_output or "").splitlines():
        line = line.strip()
        if line.lower().startswith("loaded image:"):
            return line.split(":", 1)[1].strip() or None
    return None


def drill(tar: str, *, run: bool = False, runner: Runner = default_runner,
          run_timeout: float = 120.0) -> Dict[str, Any]:
    report: Dict[str, Any] = {"schema": SCHEMA, "tar": tar,
                              "tar_bytes": os.path.getsize(tar) if os.path.isfile(tar) else 0}
    if not os.path.isfile(tar):
        return {**report, "ok": False, "error": "tar 不存在"}

    rc, before_out, _ = runner(["docker", "images",
                                "--format", "{{.Repository}}:{{.Tag}} {{.ID}}"], 60)
    if rc != 0:
        return {**report, "ok": False, "error": "docker images 失败（daemon 不可用？）"}
    before = parse_images(before_out)

    started = time.time()
    rc, out, err = runner(["docker", "load", "-i", tar], 900)
    load_s = round(time.time() - started, 1)
    if rc != 0:
        return {**report, "ok": False, "stage": "load", "load_seconds": load_s,
                "error": (err or out or "")[-300:]}

    rc, after_out, _ = runner(["docker", "images",
                               "--format", "{{.Repository}}:{{.Tag}} {{.ID}}"], 60)
    after = parse_images(after_out)
    ref = parse_loaded_ref(out) or next(
        (tag for tag, img_id in after.items() if before.get(tag) != img_id), None)
    if not ref:
        return {**report, "ok": False, "stage": "identify",
                "error": "load 成功但认不出加载了哪个 tag"}

    prev = before.get(ref)
    report.update({"load_seconds": load_s, "image_ref": ref,
                   "image_id": after.get(ref),
                   "already_present": prev == after.get(ref),
                   "overwrote_existing": prev is not None and prev != after.get(ref),
                   "previous_image_id": prev})

    if run:
        report["container"] = _run_and_probe(ref, runner, run_timeout)
    report["ok"] = (not report.get("container") or report["container"].get("health_ok")) \
        and report.get("image_id") is not None
    return report


def _run_and_probe(ref: str, runner: Runner, timeout: float) -> Dict[str, Any]:
    """起一个最短命的容器探活；**无论成败都在 finally 里删掉**。"""
    container, info = None, {"started": False, "health_ok": False, "cleaned_up": False}
    try:
        started = time.time()
        # 随机宿主端口：不占用固定端口，避免和本机在跑的服务冲突
        rc, out, err = runner(["docker", "run", "-d", "--rm", "-P", ref], timeout)
        if rc != 0:
            info["error"] = (err or out or "")[-200:]
            return info
        container = (out or "").strip().splitlines()[-1]
        info["started"] = True
        time.sleep(2.0)                    # 给 redis-server 一点启动时间
        # -P 之后用 docker port 反查映射端口，再在容器内探活（不依赖宿主端口可用性）
        rc, out, _ = runner(["docker", "exec", container, "redis-cli", "ping"], 30)
        info["health_ok"] = rc == 0 and "PONG" in (out or "").upper()
        info["probe_seconds"] = round(time.time() - started, 1)
        info["image_ref"] = ref
    finally:
        if container:
            rc, _, _ = runner(["docker", "rm", "-f", container], 60)
            info["cleaned_up"] = rc == 0
    return info


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tar", required=True)
    ap.add_argument("--run", action="store_true", help="加载后起容器探活（会自行清理）")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    report = drill(args.tar, run=args.run)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: report.get(k) for k in
                      ("ok", "image_ref", "load_seconds", "already_present",
                       "overwrote_existing", "container", "error")},
                     ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
