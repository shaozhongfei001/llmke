"""跨实例共享配额：计数必须是原子的、被拒的请求不能占额度、算不出来必须 fail-closed。

三条断言对着三个真实故障形状：
1. 先自增再判断，被拒时不扣回 → 该租户本窗口内**永久**被拒（"没跑满却一直 429"）；
2. 数据库不可用时返回 allowed=True（fail-open）→ 配额形同虚设，且面板全绿；
3. 清理写成全表 DELETE → 删掉别的租户正在用的窗口，别人的额度凭空恢复。

这里用假连接实现 SELECT/INSERT/DELETE 语义（含暂存-提交-回滚），不连真库；
真库验证见 `docs/design/unified-documents-v2/EVIDENCE-SHARED-QUOTA-20261101.md`。
"""

import os
import re

import pytest

from graph_engine_adapter.quota_shared import (DDL, SQL_PRUNE, SQL_REFUND,
                                               SQL_SELECT_USED, SQL_STATS,
                                               SQL_UPSERT, SharedQuotaCounter,
                                               SharedQuotaError)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL = os.path.join(REPO, "services", "rag-alg", "index_data_service",
                   "graph_engine_adapter", "sql", "003_shared_quota.sql")


# ---------------------------------------------------------------- 假数据库
class FakeDb:
    """把表语义写成"已提交行 + 暂存行"，好让提交/回滚真正可断言。"""

    def __init__(self):
        self.rows = {}          # (tenant, window_start) -> used（已提交）
        self.staged = {}        # 同上，事务内未提交
        self.commits = 0
        self.rollbacks = 0
        self.fail_on = None     # 命中前缀即抛，用来模拟"执行到一半连接断了"

    def visible(self):
        merged = dict(self.rows)
        for key, value in self.staged.items():
            if value is None:
                merged.pop(key, None)
            else:
                merged[key] = value
        return merged

    def used(self, tenant, window_start):
        return self.rows.get((tenant, window_start))

    def commit(self):
        for key, value in self.staged.items():
            if value is None:
                self.rows.pop(key, None)
            else:
                self.rows[key] = value
        self.staged.clear()
        self.commits += 1

    def rollback(self):
        self.staged.clear()
        self.rollbacks += 1


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._one = None
        self._many = ()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        if self.db.fail_on and s.startswith(self.db.fail_on):
            raise RuntimeError("(2013, Lost connection to MySQL server during query)")
        if s.startswith("CREATE TABLE"):
            return
        if s.startswith("DELETE FROM v2_quota_window"):
            # 按真实 SQL 的谓词删：有 `tenant = %s` 才限定租户，没有就是全表删。
            # 假驱动若"替"SQL 补租户谓词，改坏 SQL 也测不出来（假绿）。
            scoped = "tenant = %s" in s
            tenant = params[0] if scoped else None
            threshold = params[-1]
            keys = set(self.db.rows) | set(self.db.staged)
            for key in [k for k in keys if k[1] < threshold and (tenant is None or k[0] == tenant)]:
                self.db.staged[key] = None
        elif s.startswith("INSERT INTO v2_quota_window"):
            tenant, window_start, _value, delta = params
            current = self.db.visible().get((tenant, window_start)) or 0
            self.db.staged[(tenant, window_start)] = current + delta
        elif s.startswith("UPDATE v2_quota_window"):
            delta, tenant, window_start = params
            current = self.db.visible().get((tenant, window_start)) or 0
            self.db.staged[(tenant, window_start)] = max(current - delta, 0)
        elif s.startswith("SELECT used FROM v2_quota_window"):
            tenant, window_start = params
            value = self.db.visible().get((tenant, window_start))
            self._one = (value,) if value is not None else None
        elif s.startswith("SELECT tenant, used FROM v2_quota_window"):
            (window_start,) = params
            self._many = tuple(sorted(
                (t, u) for (t, w), u in self.db.visible().items() if w == window_start))
        else:  # pragma: no cover
            raise AssertionError(f"未预期的 SQL: {s[:70]}")

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class FakeConn:
    def __init__(self, db):
        self.db = db

    def autocommit(self, flag):
        return None

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def close(self):
        return None


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, s):
        self.now += s


def make(db=None, clock=None, limit=3, **kwargs):
    db = db if db is not None else FakeDb()
    clock = clock or Clock()
    counter = SharedQuotaCounter(lambda: FakeConn(db), limit=limit,
                                 clock=clock, sleep=lambda s: clock.advance(s), **kwargs)
    return counter, db, clock


# ---------------------------------------------------------------- 计数语义
def test_first_take_allowed_and_used_increments():
    counter, db, clock = make(limit=3)
    first = counter.take("t-a")
    assert first["allowed"] is True
    assert first["used"] == 1 and first["limit"] == 3
    assert first["retry_after_s"] is None
    assert counter.take("t-a")["used"] == 2
    assert db.used("t-a", 1000) == 2


def test_exactly_limit_allowed_then_one_over_denied():
    counter, db, clock = make(limit=3)
    assert [counter.take("t-a")["allowed"] for _ in range(3)] == [True, True, True]
    over = counter.take("t-a")
    assert over["allowed"] is False
    assert over["used"] == 3                     # 不含被拒的这一次
    assert over["retry_after_s"] == 1.0          # 恰好站在窗口边界上 → 一整个窗口
    assert db.used("t-a", 1000) == 3


def test_denial_does_not_consume_quota():
    """被拒的请求必须扣回：不扣的话计数器会一路涨上去，本窗口内永不放行。"""
    counter, db, clock = make(limit=3)
    for _ in range(3):
        counter.take("t-a")
    for _ in range(5):
        assert counter.take("t-a")["allowed"] is False
    assert db.used("t-a", 1000) == 3             # 不是 3+5=8

    # 同一窗口内仍然不越界；换一个租户照常放行（证明计数没被写穿）
    assert counter.take("t-b")["allowed"] is True


def test_window_rollover_allows_again():
    counter, db, clock = make(limit=2, window_s=1.0)
    counter.take("t-a")
    counter.take("t-a")
    assert counter.take("t-a")["allowed"] is False

    clock.advance(1.0)                           # 下一个窗口：新行，从 0 起算
    out = counter.take("t-a")
    assert out["allowed"] is True
    assert out["used"] == 1 and out["window_start"] == 1001
    assert db.used("t-a", 1000) == 2             # 上窗口的计数保留（供对账/清理）


def test_tenants_do_not_interfere():
    counter, db, clock = make(limit=2)
    counter.take("t-a")
    counter.take("t-a")
    assert counter.take("t-a")["allowed"] is False
    other = counter.take("t-b")
    assert other["allowed"] is True and other["used"] == 1   # 计数不共享
    assert db.used("t-a", 1000) == 2 and db.used("t-b", 1000) == 1


def test_batch_n_larger_than_limit_rejected_without_consuming():
    counter, db, clock = make(limit=3)
    out = counter.take("t-a", n=5)
    assert out["allowed"] is False and out["used"] == 0
    assert db.used("t-a", 1000) == 0             # 5 个也必须原样退回
    assert counter.take("t-a")["used"] == 1      # 之后仍能正常用


# ---------------------------------------------------------------- 清理
def test_old_windows_pruned_without_touching_current():
    counter, db, clock = make(limit=5, window_s=1.0, retention_windows=3)
    db.rows = {("t-a", 900): 9, ("t-a", 1000): 0}   # 900 早于 1000-3
    counter.take("t-a")
    assert db.used("t-a", 900) is None               # 旧窗口被清掉
    assert db.used("t-a", 1000) == 1                 # 当前窗口完好


def test_prune_never_touches_other_tenants():
    """全表 DELETE 会删掉别人正在用的窗口——等于凭空还额度。"""
    assert "tenant = %s" in SQL_PRUNE        # 谓词本身要在 SQL 里，不能只靠调用方
    counter, db, clock = make(limit=5, window_s=1.0, retention_windows=3)
    db.rows = {("t-a", 900): 9, ("t-b", 900): 7}
    counter.take("t-a")
    assert db.used("t-a", 900) is None
    assert db.used("t-b", 900) == 7


def test_sql_statements_keep_their_semantics():
    """假驱动只认前缀，SQL 的算术/谓词必须单独钉住，否则改坏 SQL 也测不出来。"""
    assert "ON DUPLICATE KEY UPDATE used = used + %s" in " ".join(SQL_UPSERT.split())
    assert "SET used = GREATEST(used - %s, 0)" in " ".join(SQL_REFUND.split())
    assert "WHERE tenant = %s AND window_start = %s" in " ".join(SQL_SELECT_USED.split())
    assert "WHERE tenant = %s AND window_start < %s" in " ".join(SQL_PRUNE.split())
    assert "WHERE window_start = %s" in " ".join(SQL_STATS.split())


# ---------------------------------------------------------------- 故障语义
def test_connection_failure_is_fail_closed():
    """连不上就抛可读错误：绝不能返回 allowed=True（那是配额失效）。"""
    def broken():
        raise OSError("(2003, Can't connect to MySQL server on '127.0.0.1')")

    counter = SharedQuotaCounter(broken, limit=3)
    with pytest.raises(SharedQuotaError) as excinfo:
        counter.take("t-a")
    message = str(excinfo.value)
    assert "配额计数不可用" in message and "t-a" in message
    assert "2003" in message
    assert "allowed" not in message


def test_mid_transaction_failure_leaves_no_partial_increment():
    """自增成功、读值失败：事务回滚，不能留下"只增不退"的脏计数。"""
    counter, db, clock = make(limit=3)
    db.fail_on = "SELECT used FROM v2_quota_window"
    with pytest.raises(SharedQuotaError):
        counter.take("t-a")
    assert db.rollbacks >= 1
    assert db.rows == {}                         # 没有半截计数

    db.fail_on = None
    assert counter.take("t-a")["used"] == 1


def test_stats_reports_counts_only():
    counter, db, clock = make(limit=4)
    counter.take("t-a")
    counter.take("t-a")
    counter.take("t-b")
    out = counter.stats()
    assert out["limit"] == 4 and out["window_start"] == 1000
    assert out["tenants"] == {"t-a": {"used": 2, "limit": 4},
                              "t-b": {"used": 1, "limit": 4}}
    # 只含计数：没有请求内容、没有别的窗口
    assert set(out) == {"schema", "window_start", "window_s", "limit", "tenants"}


# ---------------------------------------------------------------- 等待
def test_wait_take_waits_until_next_window():
    counter, db, clock = make(limit=1, window_s=2.0)
    assert counter.take("t-a")["allowed"] is True
    out = counter.wait_take("t-a")
    assert out["allowed"] is True
    assert out["waited_s"] == 2.0
    assert out["window_start"] == 501


def test_wait_take_gives_up_when_timeout_shorter_than_retry():
    """等不到就别耗线程，而且**不占额度**。"""
    counter, db, clock = make(limit=1, window_s=5.0)
    counter.take("t-a")
    out = counter.wait_take("t-a", timeout=1.0)
    assert out["allowed"] is False and out["waited_s"] == 0.0
    assert db.used("t-a", 200) == 1              # 1000/5 = 200


# ---------------------------------------------------------------- 契约
def _statements(text):
    lines = [ln.strip() for ln in text.splitlines()]
    return " ".join(ln for ln in lines if ln and not ln.startswith("--"))


def _flat(text):
    return re.sub(r"\s+", " ", text).strip().rstrip(";").strip()


def test_sql_file_matches_code_ddl():
    """代码里的 DDL 与给 DBA 的 SQL 不许漂移（本地能跑、线上缺列）。"""
    with open(SQL, encoding="utf-8") as fh:
        sql = _statements(fh.read())
    assert _flat(sql) == _flat(DDL)


def test_sql_declares_primary_key_on_tenant_and_window():
    """没有主键就没有行锁，跨实例自增会退化成"发现不了冲突的两次写"。"""
    with open(SQL, encoding="utf-8") as fh:
        text = fh.read()
    assert "PRIMARY KEY (tenant, window_start)" in text
    assert "CREATE TABLE IF NOT EXISTS" in text   # DBA 重复执行不能失败
    assert "window_start BIGINT" in text and "used         INT" in text


def test_invalid_arguments_rejected():
    counter, db, clock = make(limit=3)
    with pytest.raises(TypeError):
        counter.take("t-a", n=True)              # bool 是 int 的子类，必须挡住
    with pytest.raises(ValueError):
        counter.take("t-a", n=0)
    for kwargs in ({"limit": 0}, {"window_s": 0}, {"retention_windows": 0}):
        params = {"limit": 3, **kwargs}
        with pytest.raises(ValueError):
            SharedQuotaCounter(lambda: FakeConn(FakeDb()), **params)
