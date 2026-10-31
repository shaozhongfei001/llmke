"""MySQL 版重建租约：跨机器部署时用共享数据库做选主。

文件租约只在"同一块盘"上成立（单机多进程 / 共享存储）。跨机部署必须换共享介质，
否则两台机器各有一份租约文件，谁都能抢到——等于没有租约。

与 `FileLease` 的语义保持一致（同样的 acquire/renew/release 返回值形状、同样的 fencing），
差别只在存储与互斥手段：

| | FileLease | MySqlLease |
|---|---|---|
| 互斥 | `os.mkdir` 原子创建 | `SELECT ... FOR UPDATE` 行锁 + 事务 |
| fencing | 独立计数文件 | 同一行的 `fencing` 列，接管时 +1 |
| 适用 | 单机/共享盘 | 跨机、多副本 |

`connection_factory` 由调用方注入（真实用 pymysql），测试用假连接，避免把驱动拖进核心路径。

**超时**：租约故障有两种形态——"连不上"（立刻抛）和"连上但不回包"（卡住）。
后者默认要等 `innodb_lock_wait_timeout`（50s）甚至更久，期间 dispatch 循环整轮卡死，
比抛异常更糟。所以这里把驱动超时写成默认值（connect/read/write），不依赖部署机器上的
my.cnf，也不依赖调用方记得传。`op_budget_s` 只用于**度量**（谁慢了），不做强制中断——
Python 线程无法安全打断一个卡在 C 层 recv 的调用，假装能中断就是骗人。
"""

import socket
import time
from typing import Any, Callable, Dict, Optional

SCHEMA = "llmke.graph-engine.lease.mysql.v1"
DEFAULT_TTL = 120.0
DEFAULT_KEY = "rebuild"
# 驱动层超时默认值：建连 3s、读写 8s。宁可失败重试，不要卡住整轮调度。
DEFAULT_CONNECT_TIMEOUT = 3
DEFAULT_READ_TIMEOUT = 8
DEFAULT_WRITE_TIMEOUT = 8

DDL = """
CREATE TABLE IF NOT EXISTS v2_rebuild_lease (
  lease_key  VARCHAR(64)  NOT NULL,
  owner      VARCHAR(191) NOT NULL,
  fencing    BIGINT       NOT NULL DEFAULT 0,
  expires_at DOUBLE       NOT NULL DEFAULT 0,
  taken_at   DOUBLE       NOT NULL DEFAULT 0,
  PRIMARY KEY (lease_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


class MySqlLease:
    def __init__(self, connection_factory: Callable[[], Any], *,
                 owner: Optional[str] = None,
                 ttl: float = DEFAULT_TTL,
                 lease_key: str = DEFAULT_KEY,
                 clock: Optional[Callable[[], float]] = None,
                 op_budget_s: float = 5.0):
        self._factory = connection_factory
        self.owner = owner or f"{socket.gethostname()}:{__import__('os').getpid()}"
        self.ttl = ttl
        self.lease_key = lease_key
        self._clock = clock or time.time
        self.op_budget_s = op_budget_s
        # 度量：最近一次操作耗时与"超过预算"的次数（供调度器打慢告警）
        self.last_op_s: Optional[float] = None
        self.slow_ops = 0

    def _timed(self, fn, *args):
        started = self._clock()
        try:
            return fn(*args)
        finally:
            elapsed = self._clock() - started
            self.last_op_s = round(elapsed, 3)
            if elapsed > self.op_budget_s:
                self.slow_ops += 1

    # ---------- 内部 ----------
    def _connect(self):
        conn = self._factory()
        conn.autocommit(False)
        return conn

    def ensure_schema(self) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(DDL)
            conn.commit()
        finally:
            conn.close()

    def _row(self, cur) -> Optional[Dict[str, Any]]:
        cur.execute("SELECT owner, fencing, expires_at FROM v2_rebuild_lease "
                    "WHERE lease_key = %s FOR UPDATE", (self.lease_key,))
        row = cur.fetchone()
        if not row:
            return None
        return {"owner": row[0], "fencing": int(row[1] or 0), "expires_at": float(row[2] or 0)}

    # ---------- 对外 ----------
    def holder(self) -> Optional[str]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT owner, expires_at FROM v2_rebuild_lease WHERE lease_key = %s",
                            (self.lease_key,))
                row = cur.fetchone()
            conn.commit()
        finally:
            conn.close()
        if not row or float(row[1] or 0) <= self._clock():
            return None
        return row[0]

    def acquire(self) -> Dict[str, Any]:
        return self._timed(self._acquire)

    def renew(self) -> bool:
        return self._timed(self._renew)

    def _acquire(self) -> Dict[str, Any]:
        now = self._clock()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                row = self._row(cur)          # FOR UPDATE：并发请求在这里排队
                if row is None:
                    cur.execute(
                        "INSERT INTO v2_rebuild_lease "
                        "(lease_key, owner, fencing, expires_at, taken_at) VALUES (%s,%s,%s,%s,%s)",
                        (self.lease_key, self.owner, 1, now + self.ttl, now))
                    fencing = 1
                elif row["expires_at"] <= now or row["owner"] == self.owner:
                    # 接管过期租约：fencing +1；自己续租：fencing 不变
                    fencing = row["fencing"] + (1 if row["owner"] != self.owner else 0)
                    cur.execute(
                        "UPDATE v2_rebuild_lease SET owner=%s, fencing=%s, expires_at=%s, "
                        "taken_at=%s WHERE lease_key=%s",
                        (self.owner, fencing, now + self.ttl, now, self.lease_key))
                else:
                    conn.rollback()           # 别人持有且未过期：老实让位
                    return {"schema": SCHEMA, "acquired": False, "holder": row["owner"],
                            "expires_in_s": round(row["expires_at"] - now, 1),
                            "fencing": row["fencing"]}
            conn.commit()
            return {"schema": SCHEMA, "acquired": True, "owner": self.owner,
                    "ttl": self.ttl, "fencing": fencing}
        finally:
            conn.close()

    def _renew(self) -> bool:
        now = self._clock()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                row = self._row(cur)
                if not row or row["owner"] != self.owner or row["expires_at"] <= now:
                    conn.rollback()
                    return False
                cur.execute("UPDATE v2_rebuild_lease SET expires_at=%s WHERE lease_key=%s",
                            (now + self.ttl, self.lease_key))
            conn.commit()
            return True
        finally:
            conn.close()

    def release(self) -> bool:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                row = self._row(cur)
                if row and row["owner"] == self.owner:
                    # 保留行（fencing 不能丢，否则下一次接管会从 1 重新开始）
                    cur.execute("UPDATE v2_rebuild_lease SET expires_at=0 WHERE lease_key=%s",
                                (self.lease_key,))
                    conn.commit()
                    return True
            conn.commit()
            return False
        finally:
            conn.close()


def make_pymysql_factory(**conn_kwargs) -> Callable[[], Any]:
    """按需构造 pymysql 连接工厂；驱动缺失时给出可读错误，而不是 ImportError 的栈。

    超时**默认写死在这里**：调用方忘了传，也不会退化成"连上不回包就卡 50s"。
    """
    kwargs = {"connect_timeout": DEFAULT_CONNECT_TIMEOUT,
              "read_timeout": DEFAULT_READ_TIMEOUT,
              "write_timeout": DEFAULT_WRITE_TIMEOUT, **conn_kwargs}

    def _factory():
        try:
            import pymysql
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError("MySQL 租约需要 pymysql（交付的 graph venv 未包含，需补 wheel）") from exc
        return pymysql.connect(charset="utf8mb4", **kwargs)
    return _factory
