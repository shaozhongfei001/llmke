"""重建租约（leader election）：多实例部署时只让一个实例真正重建。

为什么必须选主：两个副本各自调度 → 各自全量重建 → 算力翻倍，还互相覆盖快照。

实现选择：**文件租约**（原子创建 + 过期接管），因为它能同时覆盖两种真实场景：
- 单机多进程（多个 worker 共享一个目录）；
- 跨机共享存储（NFS/EFS 上放同一个 lease 文件）。

语义：
- `acquire()`：文件不存在或已过期 → 抢占成功；文件有效且属主是别人 → 失败（返回 holder）；
- `renew()`：只有当前属主能续租，续租失败说明租约已被别人接管，**必须停下来**；
- `release()`：只删自己的租约，不碰别人的。

注意：这是"尽量避免重复重建"，不是强一致锁。文件系统时钟漂移、网络存储延迟都可能
导致短暂双主——所以重建本身仍然要幂等（快照目录唯一 + 指针原子切换），租约只减少浪费。
"""

import contextlib
import json
import os
import shutil
import socket
import threading
import time
from typing import Any, Callable, Dict, Optional

SCHEMA = "llmke.graph-engine.lease.v1"

DEFAULT_TTL = 120.0


@contextlib.contextmanager
def lease_guard(lease: "FileLease", interval: Optional[float] = None):
    """在长任务期间后台续租。

    为什么必须有：重建可能比 TTL 更长。不续租的话，租约会在构建中途过期，
    另一个实例就会"合法地"接管并同时构建——实测正是这样出现了两次构建。
    续租失败（被接管）时把 `lost` 置真，调用方应尽快收手。
    """
    every = interval or max(0.5, lease.ttl / 3.0)

    def _beat(state):
        while not state["stop"].is_set():
            if not lease.renew():
                state["lost"] = True
                return
            state["stop"].wait(every)

    state = {"stop": threading.Event(), "lost": False}
    thread = threading.Thread(target=_beat, args=(state,), daemon=True)
    thread.start()
    try:
        yield state
    finally:
        state["stop"].set()
        thread.join(timeout=2)


class FileLease:
    def __init__(self, path: str, owner: Optional[str] = None,
                 ttl: float = DEFAULT_TTL,
                 claim_grace: float = 3.0,
                 clock: Optional[Callable[[], float]] = None):
        self.path = path
        self.owner = owner or f"{socket.gethostname()}:{os.getpid()}"
        self.ttl = ttl
        # 抢占后到写入 meta 之间存在极短窗口：这期间别的实例读不到 meta，
        # 不能当成"过期"直接清掉目录，否则会互相踩（实测会把刚抢到的锁删掉）。
        self.claim_grace = claim_grace
        self._clock = clock or time.time

    # ---------- 内部 ----------
    #
    # 用**目录**做锁本体：`os.mkdir` 在多数文件系统上是原子的，而"先读再写文件"存在 TOCTOU
    # ——两个实例同时读到"没有租约"就会双双写入、双双认为自己是主。实测正是这样出现了双主
    # （两个实例各建了一次快照）。所以锁目录 = 原子占位，元数据写目录内的 meta.json。
    @property
    def _lock_dir(self) -> str:
        return f"{self.path}.d"

    @property
    def _counter_path(self) -> str:
        # 计数器必须独立于锁目录：锁目录被删（正常释放/接管）时计数不能跟着清零，
        # 否则 fencing 会回退，旧主就能"合法"覆盖新快照。
        return f"{self.path}.fencing"

    def _next_fencing(self) -> int:
        last = 0
        try:
            with open(self._counter_path, encoding="utf-8") as fh:
                last = int(fh.read().strip() or 0)
        except (FileNotFoundError, ValueError):
            last = 0
        payload = self._read() or {}
        last = max(last, int(payload.get("fencing", 0) or 0))
        nxt = last + 1
        tmp = f"{self._counter_path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(str(nxt))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self._counter_path)
        return nxt

    def _read(self) -> Optional[Dict[str, Any]]:
        try:
            with open(os.path.join(self._lock_dir, "meta.json"), encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _write(self, payload: Dict[str, Any]) -> None:
        os.makedirs(self._lock_dir, exist_ok=True)
        tmp = os.path.join(self._lock_dir, f"meta.{os.getpid()}.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, os.path.join(self._lock_dir, "meta.json"))

    def _expired(self, payload: Optional[Dict[str, Any]]) -> bool:
        return not payload or float(payload.get("expires_at", 0)) <= self._clock()

    # ---------- 对外 ----------
    def holder(self) -> Optional[str]:
        payload = self._read()
        if self._expired(payload):
            return None
        return (payload or {}).get("owner")

    def acquire(self) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        for _ in range(3):                       # 过期接管最多重试 3 次
            try:
                os.mkdir(self._lock_dir)         # 原子占位：只有一个实例能成功
            except FileExistsError:
                payload = self._read()
                if payload is None:
                    # 目录在但 meta 还没写：说明别人刚抢到，给它 claim_grace 秒
                    try:
                        age = self._clock() - os.stat(self._lock_dir).st_mtime
                    except FileNotFoundError:
                        continue                 # 对方已释放，直接重试
                    if age < self.claim_grace:
                        return {"schema": SCHEMA, "acquired": False, "holder": "<claiming>",
                                "expires_in_s": round(self.claim_grace - age, 1)}
                    shutil.rmtree(self._lock_dir, ignore_errors=True)   # 真僵死，清掉重抢
                    continue
                if not self._expired(payload) and payload.get("owner") != self.owner:
                    return {"schema": SCHEMA, "acquired": False,
                            "holder": payload.get("owner"),
                            "expires_in_s": round(float(payload["expires_at"]) - self._clock(), 1)}
                if self._expired(payload):       # 过期：清掉再抢，抢不到就老实让位
                    shutil.rmtree(self._lock_dir, ignore_errors=True)
                    continue
                # 自己已经持有：直接续约（fencing 不变）
                current = int((payload or {}).get("fencing", 0) or 0)
                self._write({"schema": SCHEMA, "owner": self.owner,
                             "expires_at": self._clock() + self.ttl, "taken_at": self._clock(),
                             "fencing": current})
                return {"schema": SCHEMA, "acquired": True, "owner": self.owner, "ttl": self.ttl,
                        "fencing": current}
            else:
                now = self._clock()
                fencing = self._next_fencing()       # 每次真正抢到都拿一个更大的 fencing
                self._write({"schema": SCHEMA, "owner": self.owner,
                             "expires_at": now + self.ttl, "taken_at": now, "fencing": fencing})
                return {"schema": SCHEMA, "acquired": True, "owner": self.owner, "ttl": self.ttl,
                        "fencing": fencing}
        payload = self._read()
        return {"schema": SCHEMA, "acquired": False, "holder": (payload or {}).get("owner"),
                "expires_in_s": round(float((payload or {}).get("expires_at", 0)) - self._clock(), 1)}

    def renew(self) -> bool:
        payload = self._read()
        if not payload or payload.get("owner") != self.owner or self._expired(payload):
            return False
        self._write({**payload, "expires_at": self._clock() + self.ttl})
        return True

    def release(self) -> bool:
        payload = self._read()
        if payload and payload.get("owner") == self.owner:
            shutil.rmtree(self._lock_dir, ignore_errors=True)
            return True
        return False
