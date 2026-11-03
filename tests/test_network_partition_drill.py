"""网络分区演练：TCP 建连 → 对端消失 → 恢复自愈（不连真库，用本地桩对端）。

为什么单独一组：已有的租约故障测试都停在"新建连接被拒 / 连接握手挂住"，
没有覆盖"连接**已经建立并跑通过**，随后对端消失"。真实分区里故障瞬间的连接是半开的，
而且恢复后能不能自己醒过来，只能靠这种形态验出来。

这里不碰 MySQL：桩对端 + 真 TCP 代理 + 真调度器，测的是链路层与调度决策的接线，
不是 SQL 语义（SQL 语义在 test_lease_mysql.py）。
"""

import importlib.util
import os
import socket
import sys
import threading
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "netpart_drill", os.path.join(REPO, "scripts", "v2_network_partition_drill.py"))
mod = importlib.util.module_from_spec(SPEC)
sys.modules["netpart_drill"] = mod
SPEC.loader.exec_module(mod)


# --------------------------------------------------------------------------- 桩件


class StubUpstream:
    """极简对端：收到什么就回 `OK\\n`。用来替身真实 MySQL（本组不连库）。"""

    def __init__(self):
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(64)
        self._srv.settimeout(0.2)
        self.port = self._srv.getsockname()[1]
        self.accepted = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                conn, _addr = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.accepted += 1
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    @staticmethod
    def _serve(conn):
        with conn:
            try:
                while True:
                    data = conn.recv(65536)
                    if not data:
                        return
                    conn.sendall(b"OK\n")
            except OSError:
                return

    def close(self):
        self._stop.set()
        try:
            self._srv.close()
        except OSError:
            pass
        self._thread.join(timeout=2)


class LineLease:
    """走真 TCP 的极简租约（请求-应答一线协议），语义与 MySqlLease 对齐：

    - 连不上 / 对端消失就**抛异常**（不返回 acquired=False，那是"别人持有"的语义）；
    - 成功返回 `{"acquired": True, "fencing": n}`。
    """

    op_budget_s = 5.0

    def __init__(self, port, owner="drill-test", ttl=30.0):
        self.port = port
        self.owner = owner
        self.ttl = ttl
        self.fencing = 0
        self.calls = 0

    def _rpc(self, verb):
        self.calls += 1
        with socket.create_connection(("127.0.0.1", self.port), timeout=1.0) as sock:
            sock.sendall(f"{verb}\n".encode())
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(64)
                if not chunk:
                    raise ConnectionError(f"{verb}: 对端在回包前关闭连接")
                data += chunk
        reply = data.decode().strip()
        if reply != "OK":
            raise ConnectionError(f"{verb}: 非法应答 {reply!r}")

    def acquire(self):
        self._rpc("ACQUIRE")
        self.fencing += 1
        return {"acquired": True, "owner": self.owner, "fencing": self.fencing, "ttl": self.ttl}

    def renew(self):
        self._rpc("RENEW")
        return True

    def release(self):
        return True


class LineProbe:
    """长时间持有的连接：ping 就是"再发一个请求"，分区后必然失败。

    签名与 pymysql 的 `ping(reconnect=...)` 对齐——桩不接受这个参数会让演练里抛
    TypeError，而"随便什么异常"曾被算成"连接被掐断"，那一项就是假绿的。
    """

    def __init__(self, port):
        self._sock = socket.create_connection(("127.0.0.1", port), timeout=1.0)

    def ping(self, reconnect=True):        # noqa: ARG002 - 桩不重连，只为对齐接口
        self._sock.sendall(b"PING\n")
        if self._sock.recv(64) != b"OK\n":
            raise ConnectionError("probe: 对端不再应答")

    def close(self):
        try:
            self._sock.close()
        except OSError:
            pass


def wait_for(predicate, timeout=2.0, interval=0.01):
    """计数字段是转发线程里加的，回包可能先到：断言前等到位，避免偶发。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def make_scheduler(lease, runner=None):
    built = []

    def build_once(batch):
        built.append(len(batch))
        return (runner or (lambda b: {"written": 0}))(batch)

    coord = mod.RebuildCoordinator(build_once)
    sched = mod.RebuildScheduler(coord, debounce=0.0, idle_poll=0.0,
                                 sleep=lambda _s: None, lease=lease,
                                 lease_error_backoff=0.0)
    coord.request("upload", ["f-1"])
    return sched, built


# --------------------------------------------------------------------------- 夹具


@pytest.fixture
def upstream():
    server = StubUpstream()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def proxy(upstream):
    part = mod.TcpPartitionProxy("127.0.0.1", upstream.port)
    part.start()
    try:
        yield part
    finally:
        part.stop()


# --------------------------------------------------------------------------- 用例


def test_proxy_relays_request_and_response(proxy, upstream):
    """先证转发真的通了：不通的话后面"分区后失败"毫无意义。"""
    with socket.create_connection(("127.0.0.1", proxy.port), timeout=2.0) as sock:
        sock.sendall(b"PING\n")
        assert sock.recv(64) == b"OK\n"

    assert proxy.counters["accepted"] == 1
    assert proxy.counters["bytes_c2s"] == len(b"PING\n")
    assert wait_for(lambda: proxy.counters["bytes_s2c"] == len(b"OK\n"))
    assert upstream.accepted == 1


def test_acquire_succeeds_through_proxy(proxy):
    lease = LineLease(proxy.port)
    result = lease.acquire()
    assert result["acquired"] is True
    assert result["fencing"] == 1
    assert proxy.counters["killed_conns"] == 0        # 还没分区，没有任何连接被掐


def test_cut_breaks_acquire_with_readable_error(proxy):
    lease = LineLease(proxy.port)
    lease.acquire()

    proxy.cut()

    with pytest.raises(OSError) as excinfo:
        lease.acquire()
    message = str(excinfo.value)
    assert message.strip()                                  # 不是空错误
    lowered = message.lower()                               # 拒绝/重置都算"对端消失"，都要能读懂
    assert ("refused" in lowered or "reset" in lowered or "aborted" in lowered
            or "连接" in message), message
    assert proxy.counters["cuts"] == 1


def test_cut_kills_established_connection(proxy, upstream):
    """真分区语义：连接**先建立**，随后被掐断 —— 不是"连不上"。"""
    sock = socket.create_connection(("127.0.0.1", proxy.port), timeout=2.0)
    sock.sendall(b"PING\n")
    assert sock.recv(64) == b"OK\n"                   # 已建立且跑通过
    assert proxy.counters["accepted"] == 1

    killed = proxy.cut()
    assert killed == 1                                 # 掐断的正是那条已建立连接
    assert proxy.counters["killed_conns"] == 1

    sock.settimeout(2.0)
    try:
        data = sock.recv(64)
        assert data == b""                             # 对端消失：读到 EOF
    except ConnectionResetError:
        pass                                           # 或者被 RST，同样算被掐断
    finally:
        sock.close()


def test_restore_lets_same_lease_reacquire(proxy):
    lease = LineLease(proxy.port)
    assert lease.acquire()["acquired"] is True

    proxy.cut()
    with pytest.raises(OSError):
        lease.acquire()

    port_before = proxy.port
    proxy.restore()
    assert proxy.port == port_before                    # 端口不变：连接串不用改

    result = lease.acquire()                            # 同一个 lease 对象自愈
    assert result["acquired"] is True
    assert result["fencing"] == 2
    assert proxy.counters["restores"] == 1


def test_scheduler_returns_lease_error_and_zero_builds_during_cut(proxy):
    lease = LineLease(proxy.port)
    sched, built = make_scheduler(lease)

    proxy.cut()
    cycle = sched.run_cycle()

    assert cycle["action"] == "LEASE_ERROR"
    assert "Connection" in cycle["error"] or "refused" in cycle["error"].lower()
    stats = sched.stats()
    assert stats["lease_errors"] >= 1
    assert stats["builds"] == 0
    assert built == []                                  # fail-closed：构建体一次都没被调


def test_scheduler_recovers_after_restore(proxy):
    lease = LineLease(proxy.port)
    sched, built = make_scheduler(lease)

    proxy.cut()
    assert sched.run_cycle()["action"] == "LEASE_ERROR"

    proxy.restore()
    cycle = sched.run_cycle()

    assert cycle["action"] not in ("LEASE_ERROR", "LOST_LEASE")
    assert cycle["action"] == "BUILT"
    assert built == [1]
    assert sched.stats()["lease_errors"] == 1           # 恢复后不再累加


def test_drill_reports_fail_instead_of_raising_when_link_dead():
    """演练脚本"连不上"时必须给出 status=FAIL 的可读报告，不是一屏栈。"""

    class DeadLease:
        def acquire(self):
            raise ConnectionError("(2003, \"Can't connect to MySQL server on '127.0.0.1'\")")

        def renew(self):
            raise ConnectionError("server has gone away")

    report = mod.run_drill(port=1, lease_builder=lambda cfg, port: DeadLease(),
                           probe_opener=lambda cfg, port: None)

    assert report["status"] == "FAIL"
    assert report["phase"]["before"]["acquired"] is False
    assert "ConnectionError" in report["phase"]["before"]["error_type"]
    assert "链路就不通" in report["reason"]
    assert report["phase"]["restored"] == {}            # 没进到后两段，不伪造数据
    assert "error" not in report                        # 是判定失败，不是未捕获异常


def test_drill_passes_when_partition_and_recovery_behave(proxy):
    """把桩链路接进真演练：三段判定必须整体 PASS。"""
    report = mod.run_drill(port=proxy.upstream[1],
                           lease_builder=lambda cfg, port: LineLease(port),
                           probe_opener=lambda cfg, port: LineProbe(port),
                           proxy_factory=lambda _h, _p: proxy,
                           restore_deadline_s=5.0)

    assert report["status"] == "PASS", report
    assert report["phase"]["before"]["acquired"] is True
    assert report["phase"]["cut"]["error_type"] != "NONE"
    assert report["phase"]["cut"]["scheduler_action"] == "LEASE_ERROR"
    assert report["phase"]["cut"]["scheduler_builds"] == 0
    assert report["phase"]["cut"]["established_conn"]["error_type"]   # 已建立连接被掐断
    assert report["phase"]["restored"]["acquired"] is True
    assert report["phase"]["restored"]["scheduler_action"] == "BUILT"
    assert all(report["checks"].values())


def test_drill_stops_at_before_phase_when_acquire_returns_not_acquired():
    """链路通但租约被别人占：不能当成"分区演练通过"。"""

    class BusyLease:
        def acquire(self):
            return {"acquired": False, "holder": "other-instance"}

        def renew(self):
            return False

    report = mod.run_drill(port=1, lease_builder=lambda cfg, port: BusyLease(),
                           probe_opener=lambda cfg, port: None)

    assert report["status"] == "FAIL"
    assert "holder" in report["reason"]


def test_drill_fails_when_partition_is_ineffective(proxy):
    """反证用：cut() 如果没真的断开，"分区演练"必须 FAIL，不能照样 PASS。

    没有这一条，上面那条 PASS 就可能是"什么都不检查也会过"。
    """

    class NoCutProxy:
        def __init__(self, real):
            self._real = real
            self.port = real.port
            self.upstream = real.upstream
            self.counters = real.counters

        def start(self):
            return self._real.start()

        def cut(self):
            self.counters["cuts"] += 1            # 计数涨了，但一条连接都没断
            return 0

        def restore(self):
            return self._real.restore()

        def stop(self):
            return self._real.stop()

    report = mod.run_drill(port=proxy.upstream[1],
                           lease_builder=lambda cfg, port: LineLease(port),
                           probe_opener=lambda cfg, port: LineProbe(port),
                           proxy_factory=lambda _h, _p: NoCutProxy(proxy),
                           restore_deadline_s=3.0)

    assert report["status"] == "FAIL"
    assert report["checks"]["cut_acquire_raised"] is False     # acquire 居然成功了
    assert report["checks"]["established_conn_broken"] is False
    assert report["checks"]["scheduler_lease_error"] is False


def test_cli_reports_skip_when_mysql_is_not_listening(tmp_path, capsys):
    """没有真实对端时如实 SKIP（不伪装 PASS、不抛栈），并照常落盘 --out。"""
    out = tmp_path / "netpart.json"

    code = mod.main(["--host", "127.0.0.1", "--port", "1", "--out", str(out)])

    assert code == 0                                    # SKIP 不算失败
    report = __import__("json").loads(out.read_text(encoding="utf-8"))
    assert report["status"] == "SKIP"
    assert report["missing"] == ["MySQL 未监听 127.0.0.1:1"]
    assert report["phase"] == {"before": {}, "cut": {}, "restored": {}}
    assert "SKIP" in capsys.readouterr().out


def test_lease_key_is_isolated_per_process():
    """演练只写自己的 lease_key：默认带 pid，避免踩别的实例那一行。"""
    report = mod.run_drill(port=1,
                           lease_builder=lambda cfg, port: type(
                               "L", (), {"acquire": lambda self: {"acquired": False}})(),
                           probe_opener=lambda cfg, port: None)
    assert report["lease_key"] == f"netpartition-test-{os.getpid()}"


def test_proxy_stop_releases_port(upstream):
    part = mod.TcpPartitionProxy("127.0.0.1", upstream.port)
    part.start()
    port = part.port
    part.stop()

    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                time.sleep(0.05)
        except OSError:
            return                                      # 端口已不再接受连接
    pytest.fail("stop() 之后端口仍在监听")
