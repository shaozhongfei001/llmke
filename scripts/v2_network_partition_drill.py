#!/usr/bin/env python3
"""网络分区演练：TCP 已建立 → 对端消失 → 网络恢复后自愈。

与已测过的两种形态的区别：

| | 连接拒绝（已测） | 连上不回包（已测） | 网络分区（本演练） |
|---|---|---|---|
| 故障瞬间 | 对端没起，新建连接立刻 `ECONNREFUSED` | 连得上但收不到应答，靠驱动超时兜底 | **连接先建立并跑通过**，随后对端消失 |
| 危险点 | 立刻知道 | 卡住 | 半开连接 + 恢复后可能一直醒不过来 |

为什么必须单独测：真实分区里，故障前**已经存在**的连接不会在业务第一次调用时就报错，
而且"恢复后能不能自己回来"和"故障时别误判成功"是两件事——只测前者会漏掉永远醒不过来的实例。

实现手段：**进程内 TCP 代理**（`listen 127.0.0.1:0` → 转发到真实 `127.0.0.1:13306`）。

- `cut()`：关掉监听（新连接直接被拒）**并且**掐断所有已建立连接（在途连接被拆）；
- `restore()`：在**同一端口**重新监听（`SO_REUSEADDR`），后续连接恢复正常。

因此本演练只动自己的 socket：不碰 iptables、不碰 docker、不改真实 MySQL 的配置与数据，
也不改端口 13306 —— 它只是被连接的对端。租约只写自己那条 `lease_key` 的行。

判据（`status=PASS` 需全部成立）：
1. `before`：经代理的 acquire 成功（先证明链路真的通，否则后面全是假象）；
2. `cut`：acquire 抛错（错误可读），且此前已建立的连接被掐断；
3. `cut`：真调度器 `run_cycle()` 返回 `LEASE_ERROR`（或 `LOST_LEASE`），`lease_errors>=1`、`builds==0`；
4. `restored`：同一个 lease 能重新 acquire，调度器不再报租约错误。
"""

import argparse
import json
import os
import socket
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services", "rag-alg", "index_data_service"))

from graph_engine_adapter.lease_mysql import MySqlLease, make_pymysql_factory  # noqa: E402
from graph_engine_adapter.rebuild_coordinator import RebuildCoordinator  # noqa: E402
from graph_engine_adapter.rebuild_scheduler import RebuildScheduler  # noqa: E402

SCHEMA = "llmke.v2.network-partition-drill.v1"
DEFAULT_PORT = 13306
DEFAULT_DB = "gienrag_v2_restore"          # 隔离库：只读写自己的 lease_key
DEFAULT_TTL = 30.0


def _fmt(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _tcp_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# --------------------------------------------------------------------------- 代理


class _Relay:
    """一条被转发的连接（客户端 ↔ 上游）。`kill()` 把两端一起掐断。"""

    def __init__(self, client, upstream, counters, lock):
        self.client = client
        self.upstream = upstream
        self.closed = False
        self._counters = counters
        self._lock = lock
        self._threads = []
        self._alive = 2                     # 两个方向各一个 pump，都退出才算空闲连接

    @property
    def alive(self) -> bool:
        return self._alive > 0

    def start(self):
        for src, dst, key in ((self.client, self.upstream, "bytes_c2s"),
                              (self.upstream, self.client, "bytes_s2c")):
            thread = threading.Thread(target=self._pump, args=(src, dst, key), daemon=True)
            thread.start()
            self._threads.append(thread)

    def _pump(self, src, dst, key):
        try:
            while True:
                chunk = src.recv(65536)
                if not chunk:
                    break
                dst.sendall(chunk)
                with self._lock:
                    self._counters[key] += len(chunk)
        except OSError:
            pass
        finally:
            self._alive -= 1
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def kill(self):
        for sock in (self.client, self.upstream):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        self.closed = True


class TcpPartitionProxy:
    """把 127.0.0.1:<随机端口> 的 TCP 连接原样转发到真实 MySQL 上。

    为什么要代理而不是改连接串：要造"分区"就得能在**不重启任何东西**的前提下，
    让同一批连接先通、后断、再通。代理是唯一能做到"连接级"控制又不碰系统网络配置的手段。
    """

    def __init__(self, upstream_host: str = "127.0.0.1", upstream_port: int = DEFAULT_PORT,
                 listen_host: str = "127.0.0.1", listen_port: int = 0,
                 connect_timeout: float = 3.0):
        self.upstream = (upstream_host, int(upstream_port))
        self.listen_host = listen_host
        self._port = int(listen_port)
        self._connect_timeout = connect_timeout
        self._listener = None
        self._relays = []
        self._accept_thread = None
        self._lock = threading.RLock()
        self._stopped = threading.Event()
        self.counters = {"accepted": 0, "killed_conns": 0, "idle_conns_closed": 0,
                         "cuts": 0, "restores": 0,
                         "upstream_failures": 0, "bytes_c2s": 0, "bytes_s2c": 0}

    # ---------- 对外 ----------
    @property
    def port(self) -> int:
        return self._port

    @property
    def partitioning(self) -> bool:
        return self._listener is None

    def start(self):
        with self._lock:
            if self._listener is None:
                self._listener = self._bind()
        if self._accept_thread is None or not self._accept_thread.is_alive():
            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()
        return self

    def cut(self) -> int:
        """进入分区：停止监听 + 掐断所有已建立连接。返回被掐断的连接数。"""
        with self._lock:
            listener, self._listener = self._listener, None
            relays = list(self._relays)
            self._relays = []
            self.counters["cuts"] += 1
        # 只把"还在跑"的连接算作被掐断；已经自然结束的历史连接另记一笔，
        # 否则 evidence 里会出现"掐断 5 条"这种把空闲连接也算进去的虚数。
        live = sum(1 for relay in relays if relay.alive)
        for relay in relays:
            relay.kill()
        with self._lock:
            self.counters["killed_conns"] += live
            self.counters["idle_conns_closed"] += len(relays) - live
        killed = live
        if listener is not None:
            # 只 close() 不够：另一个线程正阻塞在 accept() 时，fd 不会被真正释放，
            # 端口仍然在 listen（实测会出现"已分区却还能连上"）。shutdown 才能立刻停listen。
            try:
                listener.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                listener.close()
            except OSError:
                pass
        self._await_not_listening()
        return killed

    def _await_not_listening(self, timeout: float = 2.0) -> None:
        """等到端口真的连不上再返回：否则"分区是否生效"取决于时序，演练结论就不可信。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                probe = socket.create_connection((self.listen_host, self._port), timeout=0.2)
            except OSError:
                return
            probe.close()               # 还在 listen：这连接直接丢掉，继续等
            time.sleep(0.01)

    def restore(self) -> int:
        """从分区恢复：在原端口重新监听（端口不变，客户端连接串不用改）。"""
        with self._lock:
            if self._listener is None:
                self._listener = self._bind()
                self.counters["restores"] += 1
            return self._port

    def stop(self):
        self._stopped.set()
        with self._lock:
            listener, self._listener = self._listener, None
            relays, self._relays = list(self._relays), []
        if listener is not None:
            try:
                listener.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                listener.close()
            except OSError:
                pass
        for relay in relays:
            relay.kill()
        thread = self._accept_thread
        if thread is not None:
            thread.join(timeout=2)

    # ---------- 内部 ----------
    def _bind(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.listen_host, self._port))
        sock.listen(128)
        # 超时让 accept 定期返回：否则 cut() 关掉监听后，accept 线程会永远挂在原 socket 上
        sock.settimeout(0.2)
        self._port = sock.getsockname()[1]
        return sock

    def _accept_loop(self):
        while not self._stopped.is_set():
            listener = self._listener
            if listener is None:               # 分区中：不监听，新连接拿 ECONNREFUSED
                time.sleep(0.01)
                continue
            try:
                client, _addr = listener.accept()
            except socket.timeout:
                continue
            except OSError:                    # 监听刚被 cut() 关掉
                time.sleep(0.01)
                continue
            self._open_relay(client)

    def _open_relay(self, client):
        try:
            upstream = socket.create_connection(self.upstream, timeout=self._connect_timeout)
        except OSError:
            with self._lock:
                self.counters["upstream_failures"] += 1
            try:
                client.close()
            except OSError:
                pass
            return
        client.settimeout(None)
        upstream.settimeout(None)
        relay = _Relay(client, upstream, self.counters, self._lock)
        with self._lock:
            # 与 cut() 用同一把锁：要么"先进册、被 cut 掐断"，要么"cut 已发生、这里自己掐断"。
            # 少了这一步，cut 前一瞬建立的连接会漏过 cut（实测 probe 连接存活 → 演练假成功）。
            if self._listener is None:
                partitioned = True
            else:
                partitioned = False
                self._relays = [r for r in self._relays if not r.closed]
                self._relays.append(relay)
                self.counters["accepted"] += 1
        if partitioned:
            relay.kill()
            with self._lock:
                self.counters["killed_conns"] += 1
            return
        relay.start()


# --------------------------------------------------------------------------- 默认实现


def _cfg(host, port, user, password, database, owner, lease_key, ttl,
         connect_timeout, read_timeout, write_timeout):
    return {"host": host, "port": port, "user": user, "password": password,
            "database": database, "owner": owner, "lease_key": lease_key, "ttl": ttl,
            "connect_timeout": connect_timeout, "read_timeout": read_timeout,
            "write_timeout": write_timeout}


def _mysql_factory(cfg, proxy_port):
    """连**代理**，不直连 13306：这样 cut() 才能对同一条链路生效。"""
    return make_pymysql_factory(host="127.0.0.1", port=int(proxy_port),
                                user=cfg["user"], password=cfg["password"],
                                database=cfg["database"],
                                connect_timeout=cfg["connect_timeout"],
                                read_timeout=cfg["read_timeout"],
                                write_timeout=cfg["write_timeout"])


def build_mysql_lease(cfg, proxy_port):
    return MySqlLease(_mysql_factory(cfg, proxy_port), owner=cfg["owner"],
                      ttl=cfg["ttl"], lease_key=cfg["lease_key"])


def open_mysql_probe(cfg, proxy_port):
    """一条**长期持有**的 MySQL 连接：证明故障前 TCP 真的建立了，且 cut() 能掐断它。"""
    return _mysql_factory(cfg, proxy_port)()


def _fresh_scheduler(lease, rebuild_runner):
    """每段用一个新调度器 + 新协调器：`builds` 才能干净地读成"这一段构建了几次"。"""
    built = []

    def build_once(batch):
        built.append(len(batch))
        return rebuild_runner(batch)

    coord = RebuildCoordinator(build_once)
    sched = RebuildScheduler(coord, debounce=0.0, idle_poll=0.0, sleep=lambda _s: None,
                             lease=lease, lease_error_backoff=0.0)
    coord.request("netpartition-drill", ["f-netpartition"])
    return sched, built


def _default_rebuild_runner(batch):
    # 不跑真实图重建：本演练只验租约 + 调度决策，构建体替换成记账即可，
    # 跑真引擎会引入 LLM/embedding 依赖，反而让"租约是否恢复"被别的故障掩盖。
    return {"written": 0, "drill": True, "batch": len(batch)}


# --------------------------------------------------------------------------- 演练主体


def run_drill(*, host="127.0.0.1", port=DEFAULT_PORT, user="root", password="",
              database=DEFAULT_DB, lease_key=None, owner=None, ttl=DEFAULT_TTL,
              connect_timeout=3, read_timeout=5, write_timeout=5,
              restore_deadline_s=10.0, rebuild_runner=None,
              lease_builder=None, probe_opener=None, proxy_factory=None) -> dict:
    """跑一遍"通 → 分区 → 恢复"。**任何失败都返回 report，不向外抛栈。**"""
    lease_key = lease_key or f"netpartition-test-{os.getpid()}"
    owner = owner or f"netpartition-{os.getpid()}"
    runner = rebuild_runner or _default_rebuild_runner
    build = lease_builder or build_mysql_lease
    open_probe = probe_opener or open_mysql_probe
    make_proxy = proxy_factory or TcpPartitionProxy

    cfg = _cfg(host, port, user, password, database, owner, lease_key, ttl,
               connect_timeout, read_timeout, write_timeout)
    report = {"schema": SCHEMA,
              "phase": {"before": {}, "cut": {}, "restored": {}},
              "lease_key": lease_key,
              "schema_error": None,
              "status": "FAIL",
              "checks": {}}

    proxy = make_proxy(host, port)
    try:
        proxy.start()
        report["proxy"] = {"listen_port": proxy.port, "upstream": f"{host}:{port}"}

        lease = build(cfg, proxy.port)

        # 建表：真实部署启动时也走这一步。失败不在这里退出——那本身就是一种故障形态。
        try:
            if hasattr(lease, "ensure_schema"):
                lease.ensure_schema()
        except Exception as exc:  # noqa: BLE001
            report["schema_error"] = _fmt(exc)

        # ---------- 阶段 1：链路通（先证明不是"一直在故障"） ----------
        started = time.perf_counter()
        try:
            acquired = lease.acquire()
            report["phase"]["before"] = {
                "acquired": bool(acquired.get("acquired")),
                "latency": round(time.perf_counter() - started, 4),
                "fencing": acquired.get("fencing"),
            }
        except Exception as exc:  # noqa: BLE001
            report["phase"]["before"] = {
                "acquired": False,
                "latency": round(time.perf_counter() - started, 4),
                "error_type": type(exc).__name__,
                "error": _fmt(exc),
            }
            report["reason"] = ("演练前链路就不通：拿不到租约，无法进入分区演练"
                                "（如实报 FAIL，不抛栈）")
            return report
        if not report["phase"]["before"]["acquired"]:
            report["reason"] = "链路通但租约未拿到（holder 被占），无法证明基线可用"
            return report

        before_sched, _ = _fresh_scheduler(lease, runner)
        before_cycle = before_sched.run_cycle()
        report["scheduler"] = {"before_action": before_cycle["action"],
                               "before_builds": before_sched.stats()["builds"]}

        # 持有一条已建立的连接：分区后它必须死，这才是"真分区"而非"连不上"
        probe = None
        probe_error = None
        try:
            probe = open_probe(cfg, proxy.port)
        except Exception as exc:  # noqa: BLE001
            probe_error = _fmt(exc)

        # ---------- 阶段 2：分区 ----------
        killed = proxy.cut()
        established = {"opened": probe is not None, "killed_conns": killed}
        if probe_error is not None:
            established["open_error"] = probe_error
        if probe is not None:
            try:
                probe.ping(reconnect=False)
                established["note"] = "ping 仍成功：连接没被掐断（分区未生效）"
            except Exception as exc:  # noqa: BLE001
                established["error_type"] = type(exc).__name__
                established["error_len"] = len(_fmt(exc))
                established["error"] = _fmt(exc)
            finally:
                try:
                    probe.close()
                except Exception:  # noqa: BLE001
                    pass

        started = time.perf_counter()
        cut_error_type, cut_error = "NONE", None
        try:
            lease.acquire()
        except Exception as exc:  # noqa: BLE001
            cut_error_type, cut_error = type(exc).__name__, _fmt(exc)
        fail_latency = round(time.perf_counter() - started, 4)

        cut_sched, _ = _fresh_scheduler(lease, runner)
        cut_cycle = cut_sched.run_cycle()
        cut_stats = cut_sched.stats()

        report["phase"]["cut"] = {
            "error_type": cut_error_type,
            "error_len": len(cut_error or ""),
            "error": cut_error,
            "scheduler_action": cut_cycle["action"],
            "scheduler_builds": cut_stats["builds"],
            "scheduler_lease_errors": cut_stats["lease_errors"],
            "fail_latency": fail_latency,
            "established_conn": established,
        }

        # ---------- 阶段 3：恢复 ----------
        started = time.perf_counter()
        proxy.restore()
        restored_ok, last_error = False, None
        deadline = time.time() + restore_deadline_s
        while time.time() < deadline:
            try:
                result = lease.acquire()
                if result.get("acquired"):
                    restored_ok = True
                    break
                last_error = f"acquired=False holder={result.get('holder')}"
            except Exception as exc:  # noqa: BLE001
                last_error = _fmt(exc)
            time.sleep(0.05)
        recovered_after = round(time.perf_counter() - started, 4)

        after_sched, _ = _fresh_scheduler(lease, runner)
        after_cycle = after_sched.run_cycle()
        after_stats = after_sched.stats()

        report["phase"]["restored"] = {
            "acquired": restored_ok,
            "recovered_after_s": recovered_after,
            "last_error": last_error,
            "scheduler_action": after_cycle["action"],
            "scheduler_builds": after_stats["builds"],
        }
        report["scheduler"].update({"cut_action": cut_cycle["action"],
                                    "restored_action": after_cycle["action"],
                                    "restored_builds": after_stats["builds"]})

        # ---------- 判定 ----------
        # 注意：探测连接"报错"不等于"被掐断"。TypeError/AttributeError 是自己代码写错，
        # 若把它算成连接被掐断，这一项就永远是绿的（本演练第一版正是这么假绿的）。
        established_type = established.get("error_type")
        checks = {
            "before_link_ok": report["phase"]["before"]["acquired"] is True,
            "cut_acquire_raised": cut_error_type != "NONE",
            "cut_error_readable": bool(cut_error) and len(cut_error) >= 10,
            "established_conn_broken": bool(established_type)
            and established_type not in ("TypeError", "AttributeError", "NameError"),
            "scheduler_lease_error": cut_cycle["action"] in ("LEASE_ERROR", "LOST_LEASE"),
            "scheduler_zero_builds": cut_stats["builds"] == 0,
            "scheduler_counted_error": cut_stats["lease_errors"] >= 1,
            "restored_acquired": restored_ok,
            "scheduler_recovered": after_cycle["action"] not in ("LEASE_ERROR", "LOST_LEASE"),
        }
        report["checks"] = checks
        report["status"] = "PASS" if all(checks.values()) else "FAIL"

        try:
            lease.release()          # 只交还自己那条 lease_key
        except Exception:  # noqa: BLE001
            pass
        return report
    except Exception as exc:  # noqa: BLE001
        report["status"] = "FAIL"
        report["error"] = _fmt(exc)
        report["reason"] = "演练过程中出现未预期异常（已捕获，不抛栈）"
        return report
    finally:
        try:
            report["proxy"] = {**report.get("proxy", {}), **dict(proxy.counters)}
        except Exception:  # noqa: BLE001
            pass
        try:
            proxy.stop()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- CLI


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="网络分区演练（进程内 TCP 代理，只动自己的 socket）")
    ap.add_argument("--host", default=os.environ.get("LLMKE_TEST_MYSQL_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("LLMKE_TEST_MYSQL_PORT", str(DEFAULT_PORT))))
    ap.add_argument("--user", default=os.environ.get("LLMKE_TEST_MYSQL_USER", "root"))
    # 故意不提供 --password：命令行参数会进 shell 历史与 ps，密码只从环境变量读
    ap.add_argument("--database", default=os.environ.get("LLMKE_TEST_MYSQL_DB", DEFAULT_DB))
    ap.add_argument("--lease-key", default=None, help="默认 netpartition-test-<pid>")
    ap.add_argument("--restore-deadline", type=float, default=10.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    password = os.environ.get("LLMKE_TEST_MYSQL_PASSWORD", "")
    lease_key = args.lease_key or f"netpartition-test-{os.getpid()}"

    if _tcp_reachable(args.host, args.port):
        report = run_drill(host=args.host, port=args.port, user=args.user,
                           password=password, database=args.database,
                           lease_key=lease_key,
                           restore_deadline_s=args.restore_deadline)
    else:
        # 如实报 SKIP，不伪装成 PASS：分区演练必须有真实对端才有意义
        report = {"schema": SCHEMA,
                  "phase": {"before": {}, "cut": {}, "restored": {}},
                  "lease_key": lease_key, "schema_error": None, "status": "SKIP",
                  "missing": [f"MySQL 未监听 {args.host}:{args.port}"],
                  "checks": {}}

    report["environment"] = {"mysql": f"{args.host}:{args.port}", "database": args.database,
                             "python": sys.version.split()[0],
                             "proxy": "in-process TCP proxy (127.0.0.1, 端口随机)"}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] in ("PASS", "SKIP") else 1


if __name__ == "__main__":
    raise SystemExit(main())
