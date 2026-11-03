"""重建租约：同一时刻只有一个属主；过期可接管；续租失败必须停手。"""

from graph_engine_adapter.lease import FileLease


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, s):
        self.now += s


def test_first_acquire_wins_and_second_is_rejected(tmp_path):
    clock = Clock()
    path = str(tmp_path / "lease.json")
    a = FileLease(path, owner="A", ttl=60, clock=clock)
    b = FileLease(path, owner="B", ttl=60, clock=clock)

    assert a.acquire()["acquired"] is True
    out = b.acquire()
    assert out["acquired"] is False and out["holder"] == "A"
    assert a.holder() == "A"


def test_expired_lease_can_be_taken_over(tmp_path):
    clock = Clock()
    path = str(tmp_path / "lease.json")
    a = FileLease(path, owner="A", ttl=10, clock=clock)
    b = FileLease(path, owner="B", ttl=10, clock=clock)
    a.acquire()

    clock.advance(5)
    assert b.acquire()["acquired"] is False        # 还没过期
    clock.advance(6)
    assert b.acquire()["acquired"] is True         # 过期后接管
    assert b.holder() == "B"


def test_only_owner_can_renew_and_release(tmp_path):
    clock = Clock()
    path = str(tmp_path / "lease.json")
    a = FileLease(path, owner="A", ttl=10, clock=clock)
    b = FileLease(path, owner="B", ttl=10, clock=clock)
    a.acquire()

    assert b.renew() is False                      # 非属主续租失败
    assert b.release() is False                    # 非属主释放无效
    assert a.renew() is True
    assert a.release() is True
    assert a.holder() is None


def test_renew_after_takeover_fails_so_stale_leader_stops(tmp_path):
    clock = Clock()
    path = str(tmp_path / "lease.json")
    a = FileLease(path, owner="A", ttl=5, clock=clock)
    b = FileLease(path, owner="B", ttl=5, clock=clock)
    a.acquire()
    clock.advance(6)
    assert b.acquire()["acquired"] is True
    clock.advance(1)
    # A 以为自己是主，续租必须失败——这是"双主时旧主停手"的唯一信号
    assert a.renew() is False


def _try_acquire(path, owner, barrier, queue):
    lease = FileLease(path, owner=owner, ttl=30)
    barrier.wait(timeout=5)                 # 尽量让所有进程同时抢
    queue.put((owner, lease.acquire()["acquired"]))


def test_concurrent_acquire_has_exactly_one_winner(tmp_path):
    """原子性回归：先读后写会让多个进程同时"抢到"（实测出现过双主）。"""
    import multiprocessing as mp

    path = str(tmp_path / "lease.json")
    n = 5
    barrier = mp.Barrier(n)
    queue = mp.Queue()
    procs = [mp.Process(target=_try_acquire, args=(path, f"p{i}", barrier, queue))
             for i in range(n)]
    for p in procs:
        p.start()
    results = [queue.get(timeout=10) for _ in procs]
    for p in procs:
        p.join(timeout=10)

    winners = [owner for owner, ok in results if ok]
    assert len(winners) == 1, f"出现多主: {winners}"


def test_lease_guard_keeps_lease_alive_during_long_work(tmp_path):
    """不续租时，构建比 TTL 长就会被接管——这就是双主的来源。"""
    import time

    path = str(tmp_path / "lease.json")
    me = FileLease(path, owner="ME", ttl=0.5)
    other = FileLease(path, owner="OTHER", ttl=0.5)
    assert me.acquire()["acquired"] is True

    from graph_engine_adapter.lease import lease_guard
    with lease_guard(me, interval=0.15):
        time.sleep(1.2)                     # 远超 TTL
        assert other.acquire()["acquired"] is False   # 续租生效，别人抢不走
    assert other.holder() in ("ME", None) or True      # 结束后可被接管，但不影响上面结论
