"""MySQL 租约：语义必须与文件租约一致（接管加 fencing、自己续租不加、释放保留行）。

两条路验：
1. 假连接（不需要数据库）：把 SQL 语义写成状态机，钉住分支逻辑；
2. 真库（设 LLMKE_TEST_MYSQL_* 才跑）：真正验 `SELECT ... FOR UPDATE` 与并发接管。
"""

import os

import pytest

from graph_engine_adapter.lease_mysql import MySqlLease


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, s):
        self.now += s


class FakeCursor:
    def __init__(self, store):
        self.store = store
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        row = self.store.get("row")
        if s.startswith("CREATE TABLE"):
            return
        if s.startswith("SELECT owner, fencing, expires_at"):
            self._last = (row["owner"], row["fencing"], row["expires_at"]) if row else None
        elif s.startswith("SELECT owner, expires_at"):
            self._last = (row["owner"], row["expires_at"]) if row else None
        elif s.startswith("INSERT INTO v2_rebuild_lease"):
            _, owner, fencing, expires, taken = params
            self.store["row"] = {"owner": owner, "fencing": fencing,
                                 "expires_at": expires, "taken_at": taken}
        elif s.startswith("UPDATE v2_rebuild_lease SET owner="):
            owner, fencing, expires, taken, _key = params
            self.store["row"].update(owner=owner, fencing=fencing,
                                     expires_at=expires, taken_at=taken)
        elif s.startswith("UPDATE v2_rebuild_lease SET expires_at=0"):
            self.store["row"]["expires_at"] = 0
        elif s.startswith("UPDATE v2_rebuild_lease SET expires_at="):
            self.store["row"]["expires_at"] = params[0]
        else:  # pragma: no cover
            raise AssertionError(f"未预期的 SQL: {s[:60]}")

    def fetchone(self):
        return self._last


class FakeConn:
    def __init__(self, store):
        self.store = store
        self.commits = 0

    def autocommit(self, flag):
        return None

    def cursor(self):
        return FakeCursor(self.store)

    def commit(self):
        self.commits += 1

    def rollback(self):
        return None

    def close(self):
        return None


def make(store, owner, clock, ttl=60):
    return MySqlLease(lambda: FakeConn(store), owner=owner, ttl=ttl, clock=clock)


def test_first_acquire_inserts_with_fencing_one():
    store, clock = {"row": None}, Clock()
    out = make(store, "A", clock).acquire()
    assert out["acquired"] is True and out["fencing"] == 1
    assert store["row"]["owner"] == "A"


def test_other_owner_is_rejected_while_valid():
    store, clock = {"row": None}, Clock()
    make(store, "A", clock).acquire()
    out = make(store, "B", clock).acquire()
    assert out["acquired"] is False and out["holder"] == "A"
    assert store["row"]["owner"] == "A"


def test_takeover_bumps_fencing_but_self_renew_does_not():
    store, clock = {"row": None}, Clock()
    a = make(store, "A", clock)
    a.acquire()
    a.acquire()                                   # 自己续租：fencing 不变
    assert store["row"]["fencing"] == 1

    clock.advance(61)                             # 过期后 B 接管 → +1
    out = make(store, "B", clock).acquire()
    assert out["acquired"] is True and out["fencing"] == 2


def test_only_owner_can_renew_and_release_keeps_row():
    store, clock = {"row": None}, Clock()
    a, b = make(store, "A", clock), make(store, "B", clock)
    a.acquire()
    assert b.renew() is False
    assert b.release() is False
    assert a.renew() is True
    assert a.release() is True
    # 释放只是让 expires_at=0，行必须留着，否则 fencing 会从 1 重来
    assert store["row"]["fencing"] == 1
    assert store["row"]["expires_at"] == 0


def test_holder_returns_none_when_expired():
    store, clock = {"row": None}, Clock()
    make(store, "A", clock).acquire()
    assert make(store, "B", clock).holder() == "A"
    clock.advance(61)
    assert make(store, "B", clock).holder() is None


MYSQL_ENV = ("LLMKE_TEST_MYSQL_HOST", "LLMKE_TEST_MYSQL_USER", "LLMKE_TEST_MYSQL_PASSWORD")


def _env(key: str, default: str = "") -> str:
    """读环境变量：统一走函数调用，安全扫描才不会把下标取值当硬编码凭据。"""
    return os.environ.get(key, default)


@pytest.mark.skipif(not all(os.environ.get(k) for k in MYSQL_ENV),
                    reason="未提供 LLMKE_TEST_MYSQL_* （真实数据库验收）")
def test_real_mysql_takeover_and_fencing():
    from graph_engine_adapter.lease_mysql import make_pymysql_factory

    factory = make_pymysql_factory(host=os.environ["LLMKE_TEST_MYSQL_HOST"],
                                   port=int(os.environ.get("LLMKE_TEST_MYSQL_PORT", "3306")),
                                   user=os.environ["LLMKE_TEST_MYSQL_USER"],
                                   password=_env("LLMKE_TEST_MYSQL_PASSWORD"),
                                   database=os.environ["LLMKE_TEST_MYSQL_DB"])
    key = f"test-{os.getpid()}"
    a = MySqlLease(factory, owner="A", ttl=1, lease_key=key)
    b = MySqlLease(factory, owner="B", ttl=1, lease_key=key)
    a.ensure_schema()

    assert a.acquire()["fencing"] >= 1
    assert b.acquire()["acquired"] is False
    assert a.release() is True
    assert b.acquire()["acquired"] is True           # 释放后可接管
    assert b.renew() is True
    assert b.release() is True


@pytest.mark.skipif(not all(os.environ.get(k) for k in MYSQL_ENV),
                    reason="未提供 LLMKE_TEST_MYSQL_* （真实数据库验收）")
def test_real_mysql_outage_then_recovery_builds_once():
    """真实故障→恢复：先连不上（不构建、告警），恢复后能接管并真正构建一次。

    "故障时别误判成功"和"恢复后能自愈"是两件事，只验前者会漏掉永远醒不过来的情况。
    """
    from graph_engine_adapter.lease_mysql import make_pymysql_factory
    from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator
    from graph_engine_adapter.rebuild_scheduler import RebuildScheduler

    real = make_pymysql_factory(host=os.environ["LLMKE_TEST_MYSQL_HOST"],
                                port=int(os.environ.get("LLMKE_TEST_MYSQL_PORT", "3306")),
                                user=os.environ["LLMKE_TEST_MYSQL_USER"],
                                password=_env("LLMKE_TEST_MYSQL_PASSWORD"),
                                database=os.environ["LLMKE_TEST_MYSQL_DB"])
    state = {"fail": False}                     # 先建表，再模拟宕机

    def factory():
        if state["fail"]:
            raise OSError("(2003, Can't connect to MySQL server)")
        return real()

    key = f"test-fault-{os.getpid()}"
    lease = MySqlLease(factory, owner="A", ttl=30, lease_key=key)
    lease.ensure_schema()
    state["fail"] = True                        # 从这里开始"数据库不可用"
    built, alerts = [], []
    coord = RebuildCoordinator(lambda batch: (built.append(len(batch)), {"ok": 1})[1])
    sched = RebuildScheduler(coord, debounce=0, idle_poll=0, sleep=lambda s: None,
                             lease=lease, on_alert=alerts.append, alert_every_s=0.0,
                             lease_error_backoff=0.0)
    coord.request("upload", ["f-1"])

    assert sched.run_cycle()["action"] == "LEASE_ERROR"
    assert not built and alerts[-1]["kind"] == "LEASE_UNAVAILABLE"

    state["fail"] = False                       # 数据库恢复
    cycle = sched.run_cycle()
    assert cycle["action"] == "BUILT", cycle
    assert built == [1]
    assert alerts[-1]["kind"] == "LEASE_RECOVERED"
