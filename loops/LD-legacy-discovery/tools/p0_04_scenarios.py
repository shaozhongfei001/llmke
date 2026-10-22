#!/usr/bin/env python3
"""P0-04 五场景协议模拟（**模拟验证，不得计入 P0-04 关闭证据**）。

为什么是模拟：真实关闭需要可运行检索链与四套存储（MySQL/ES/Milvus/Neo4j），
当前环境不具备。本脚本只验证「协议设计是否自洽、是否挡住已知混代路径」。

设计要点（对应 P0-04 decision_required 四条）：
1. generation manifest 不可变 —— 修正只能新开 generation；
2. 每 KB 单原子激活指针 —— 不逐后端切换；
3. 写入必须带 (kb_id, generation_id, fencing_token)，非当前代必须显式报错；
4. 幂等键必须含内容哈希 —— 否则同配置下内容覆盖无法区分。

每个场景都配一个「变异体」：把关键约束改坏，断言必须由 PASS 变 FAIL。
变异体全部 FAIL 才说明断言非空转。
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path


class ProtocolError(Exception):
    pass


def content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class Store:
    """四后端的最小模型：任何一次激活要么全切，要么不切。"""

    BACKENDS = ("mysql", "es", "milvus", "neo4j")

    def __init__(self):
        self.active = {}          # kb -> generation
        self.data = {}            # (kb, generation) -> {backend: [records]}
        self.fail = set()         # 注入失败的 backend

    def provision(self, kb, generation):
        self.data[(kb, generation)] = {b: [] for b in self.BACKENDS}

    def write(self, kb, generation, backend, record):
        if backend in self.fail:
            raise ProtocolError(f"backend {backend} unavailable")
        self.data[(kb, generation)][backend].append(record)

    def activate(self, kb, generation):
        """原子激活：任一后端不可用则整体不切（不逐后端切换）。"""
        for b in self.BACKENDS:
            if b in self.fail:
                raise ProtocolError(f"activation aborted: {b} not ready")
        self.active[kb] = generation

    def readable(self, kb):
        """当前可读代次集合。协议要求：任意时刻只应有一个。"""
        gen = self.active.get(kb)
        return set() if gen is None else {gen}


class Index:
    def __init__(self, store, strict_idempotency=True):
        self.store = store
        self.strict = strict_idempotency     # False = 变异体：用旧幂等键
        self.fence = {}                      # kb -> 已见最大 fencing_token
        self.manifest = {}                   # kb -> {generation: manifest dict}
        self.active_gen = {}                 # kb -> 读激活代次
        self.write_target = {}               # kb -> 允许写入的代次（构建期=新代）

    def open_generation(self, kb, generation, manifest):
        if generation in self.manifest.get(kb, {}):
            raise ProtocolError("generation manifest is immutable; open a new generation")
        self.manifest.setdefault(kb, {})[generation] = dict(manifest)
        self.store.provision(kb, generation)
        self.write_target[kb] = generation   # 构建期先写新代，读仍指旧代

    def activate(self, kb, generation):
        self.store.activate(kb, generation)  # 任一后端失败则抛错，两个指针都不动
        self.active_gen[kb] = generation
        self.write_target[kb] = generation
        self.fence.setdefault(kb, 0)

    def idempotency_key(self, kb, file_id, config_version, payload):
        if self.strict:
            return (kb, file_id, config_version, content_hash(payload))
        return (kb, file_id, config_version)      # 旧行为：同配置下无法区分内容

    def write_chunk(self, kb, generation, fencing_token, backend, file_id,
                    config_version, payload: bytes):
        if self.write_target.get(kb) != generation:
            raise ProtocolError(
                f"stale generation: writing {generation} while write target is {self.write_target.get(kb)}")
        if fencing_token < self.fence.get(kb, 0):
            raise ProtocolError(
                f"fenced out: token {fencing_token} < {self.fence.get(kb, 0)}")
        self.fence[kb] = max(self.fence.get(kb, 0), fencing_token)
        key = self.idempotency_key(kb, file_id, config_version, payload)
        rec = {"key": key, "sha256": content_hash(payload), "bytes": len(payload)}
        self.store.write(kb, generation, backend, rec)
        return rec

    def records(self, kb, generation, backend):
        return self.store.data[(kb, generation)][backend]


def scenario_partial_backend_failure(mutant=False):
    s = Store(); idx = Index(s)
    idx.open_generation("kb1", 1, {"content_hash": "h1"})
    idx.activate("kb1", 1)
    for b in Store.BACKENDS:
        idx.write_chunk("kb1", 1, 1, b, "f1", "c1", b"v1")
    idx.open_generation("kb1", 2, {"content_hash": "h2"})
    for b in Store.BACKENDS:
        idx.write_chunk("kb1", 2, 2, b, "f1", "c1", b"v2")
    s.fail.add("milvus")                      # 一个后端不可用
    try:
        if mutant:
            s.active["kb1"] = 2               # 变异：绕过原子性直接改指针
        else:
            idx.activate("kb1", 2)
        activated = True
    except ProtocolError:
        activated = False
    mixed = len(s.readable("kb1")) != 1
    return {
        "activated": activated,
        "readable_generations": sorted(s.readable("kb1")),
        "pass": (not activated) and not mixed,
    }


def scenario_activation_interrupted(mutant=False):
    """切换中断：预检阶段抛错，指针必须停在旧代；恢复后仍只能单代可读。"""
    s = Store(); idx = Index(s)
    idx.open_generation("kb1", 1, {"content_hash": "h1"})
    idx.activate("kb1", 1)
    idx.write_chunk("kb1", 1, 1, "mysql", "f1", "c1", b"v1")
    idx.open_generation("kb1", 2, {"content_hash": "h2"})
    idx.write_chunk("kb1", 2, 2, "mysql", "f1", "c1", b"v2")
    s.fail.add("es")                          # 中断点
    try:
        if mutant:
            s.active["kb1"] = 2
            ok = True
        else:
            idx.activate("kb1", 2); ok = True
    except ProtocolError:
        ok = False
    gens = sorted(s.readable("kb1"))
    return {"activated": ok, "readable_generations": gens,
            "pass": (not ok) and gens == [1]}


def scenario_content_overwrite(mutant=False):
    """内容覆盖：同 (kb,file,config) 但内容不同，必须能被区分。"""
    s = Store(); idx = Index(s, strict_idempotency=not mutant)
    idx.open_generation("kb1", 1, {"content_hash": "h1"})
    idx.activate("kb1", 1)
    a = idx.write_chunk("kb1", 1, 1, "mysql", "f1", "c1", b"content-A")
    b = idx.write_chunk("kb1", 1, 1, "mysql", "f1", "c1", b"content-B")
    distinguishable = a["key"] != b["key"]
    return {"key_a": str(a["key"])[:60], "distinguishable": distinguishable,
            "pass": distinguishable}


def scenario_late_retry(mutant=False):
    """迟到重试：旧代任务在切换后到达，必须被 fencing 挡住。"""
    s = Store(); idx = Index(s)
    idx.open_generation("kb1", 1, {"content_hash": "h1"})
    idx.activate("kb1", 1)
    idx.write_chunk("kb1", 1, 5, "mysql", "f1", "c1", b"v1")
    idx.open_generation("kb1", 2, {"content_hash": "h2"})
    idx.write_chunk("kb1", 2, 9, "mysql", "f1", "c1", b"v2")
    idx.activate("kb1", 2)
    try:
        if mutant:
            # 变异：绕过 fencing，让旧代迟到任务直接写入新代
            s.data[("kb1", 2)]["mysql"].append(
                {"key": ("kb1", "f1", "c1"), "sha256": content_hash(b"late"), "bytes": 4})
            rejected = False
        else:
            # 迟到任务：代次已是 2（匹配），但 token 6 < 已见 9 → 必须被 fencing 挡
            idx.write_chunk("kb1", 2, 6, "mysql", "f1", "c1", b"late")
            rejected = False
    except ProtocolError:
        rejected = True
    polluted = any(r["sha256"] == content_hash(b"late") for r in idx.records("kb1", 2, "mysql"))
    return {"rejected": rejected, "new_generation_polluted": polluted,
            "pass": rejected and not polluted}


def scenario_old_service_rollback(mutant=False):
    """旧服务回退：切到 gen2 后旧服务（gen1 代码）继续写，必须被拒。"""
    s = Store(); idx = Index(s)
    idx.open_generation("kb1", 1, {"content_hash": "h1"})
    idx.activate("kb1", 1)
    idx.open_generation("kb1", 2, {"content_hash": "h2"})
    idx.write_chunk("kb1", 2, 3, "mysql", "f1", "c1", b"v2")
    idx.activate("kb1", 2)
    try:
        if mutant:
            s.data[("kb1", 1)]["mysql"].append({"key": ("kb1", "f1", "c1"), "sha256": "x", "bytes": 1})
            rejected = False
        else:
            idx.write_chunk("kb1", 1, 4, "mysql", "f1", "c1", b"from-old-service")
            rejected = False
    except ProtocolError:
        rejected = True
    return {"rejected": rejected, "pass": rejected}


SCENARIOS = {
    "S1_partial_backend_failure": scenario_partial_backend_failure,
    "S2_activation_interrupted": scenario_activation_interrupted,
    "S3_content_overwrite": scenario_content_overwrite,
    "S4_late_retry": scenario_late_retry,
    "S5_old_service_rollback": scenario_old_service_rollback,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    results, mutants, failures = [], [], []
    for name, fn in SCENARIOS.items():
        r = fn()
        m = fn(mutant=True)
        results.append({"scenario": name, **r})
        mutants.append({"scenario": name, "mutant_pass": m["pass"]})
        if not r["pass"]:
            failures.append(f"{name}: 协议未挡住混代路径")
        if m["pass"]:
            failures.append(f"{name}: 变异体竟然通过 → 断言空转")

    payload = {
        "scope": "P0-04 协议模拟（SIMULATED）",
        "warning": "不得计入 P0-04 关闭证据；真实关闭需可运行检索链与四套存储",
        "scenarios": results,
        "mutation_check": mutants,
        "all_mutants_failed": all(not m["mutant_pass"] for m in mutants),
        "failures": failures,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"scenarios={len(results)} passed={sum(1 for r in results if r['pass'])}")
    print(f"mutants_rejected={sum(1 for m in mutants if not m['mutant_pass'])}/{len(mutants)}")
    for f in failures:
        print("FAIL:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
