#!/usr/bin/env python3
"""A14 运行与恢复（任务书 §5.2 A14）。

判据：候选制品重建重启后实际运行版本正确；故障自愈或明确可重试；数据/索引/权限/引用恢复一致。
写操作边界：重启、断连、kill worker、升级回退都会改运行态，本轮不执行。
只读可证伪的部分（这条最硬，因为它直接否掉"我改了源码但进程没加载"）：
  N1 监听进程的启动时间必须晚于它加载的制品/源码最后一次修改
     —— 制品比进程新 = STALE_JAR/STALE_SRC，运行中的不是当前候选
  N2 进程启动时间必须是可取得的真实值（取不到就判失败，不能默认"应该是新的"）
"""
import os
import re
import subprocess
from datetime import datetime

import common as C

ID = "A14"
TITLE = "运行与恢复：运行中的进程/制品是当前候选（无 STALE）"
WRITES = True

PORTS = {"8088": "网关(Java)", "19529": "图解析服务(Python)"}


def _pid_on(port):
    p = subprocess.run(["ss", "-lntp"], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if f":{port}" not in line:
            continue
        m = re.search(r"pid=(\d+)", line)
        if m:
            return m.group(1)
    return None


def _start(pid):
    p = subprocess.run(["ps", "-o", "lstart=", "-p", pid], capture_output=True, text=True)
    s = " ".join(p.stdout.split())
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %Y")
    except Exception:
        return None


def _artifact_mtime(pid):
    """Java: /proc/pid/cmdline 里的 -jar 文件；Python: /proc/pid/cwd + 服务源码。"""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            args = f.read().split(b"\x00")
    except OSError:
        return None, "cmdline 不可读"
    for a in args:
        s = a.decode("utf-8", "replace")
        if s.endswith(".jar") and os.path.exists(s):
            return datetime.fromtimestamp(os.path.getmtime(s)), s
    try:
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None, "cwd 不可读"
    cand = os.path.join(cwd, "graph_service.py")
    if os.path.exists(cand):
        return datetime.fromtimestamp(os.path.getmtime(cand)), cand
    return None, f"未定位制品（cwd={cwd}）"


def run():
    checks = []
    for port, name in PORTS.items():
        pid = _pid_on(port)
        if not pid:
            checks.append(C.chk(f"N2 {name} 进程可定位", False, f"端口 {port} 未解析到 pid"))
            continue
        st = _start(pid)
        mt, path = _artifact_mtime(pid)
        if st is None or mt is None:
            checks.append(C.chk(f"N2 {name} 启动时间与制品时间可取得", False,
                                f"pid={pid} start={st} artifact={path} mtime={mt}"))
            continue
        stale = mt > st
        checks.append(C.chk(f"N1 反例：{name} 未 STALE（制品早于进程启动）", not stale,
                            f"pid={pid} 启动={st} 制品={path} mtime={mt} "
                            f"→ {'制品比进程新，进程未加载当前候选' if stale else '一致'}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="重启/断连/worker 退出/恢复副本回退属写操作，本轮不执行")
