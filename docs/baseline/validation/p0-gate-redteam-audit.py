"""P0 关闭闸门红队审计：不改仓库，只在 /tmp 造夹具，验证 check() 是否真能拦住伪造关闭。

每个用例都构造一个"看起来像 CLOSED"的登记+档案，然后断言 check() 必须报错，
且错误信息指向我们注入的那个缺陷（而不是别的无关原因）。
"""
import json
import shutil
import sys
from pathlib import Path

REPO = Path("/home/szf/data/dev/llmke-r8")
sys.path.insert(0, str(REPO / "scripts"))

from contract_runtime import canonical, digest, filehash, load  # noqa: E402
from p0_closure_check import check  # noqa: E402

BASE = Path("/tmp/p0audit/run")


def build_root():
    if BASE.exists():
        shutil.rmtree(BASE)
    root = BASE
    (root / "docs/policies").mkdir(parents=True)
    (root / "docs/registers").mkdir(parents=True)
    (root / "evidence").mkdir(parents=True)
    shutil.copy(REPO / "docs/policies/P0-POLICY.yaml", root / "docs/policies/P0-POLICY.yaml")
    (root / "VERSION").write_text("1.1.1\n")
    (root / "evidence/fact.txt").write_text("real runtime route export\n")
    return root


def base_register(root):
    """把所有项置 CLOSED，dossier 结构完整——作为"合格"基线，再逐项破坏。"""
    from baseline_support import snapshot

    reg = load(REPO / "docs/registers/P0-CLOSURE.yaml")
    for it in reg["items"]:
        pid = it["id"]
        ev = root / f"evidence/{pid}-fact.txt"
        ev.write_text(f"{pid} evidence\n")
        dossier = {
            "blocker_id": pid,
            "status": "CLOSED",
            "source_snapshot_sha256": snapshot(root),
            "answers": {
                f"D{i+1:02}": {"conclusion": "decided", "evidence": [
                    {"path": f"evidence/{pid}-fact.txt", "sha256": filehash(ev)}]}
                for i in range(len(it["decision_required"]))
            },
            "verified_tests": [{"name": "compat", "result": "PASS"}],
            "approvals": [],
        }
        p = root / f"evidence/{pid}-dossier.json"
        p.write_text(json.dumps(dossier, ensure_ascii=False, indent=1))
        it["status"] = "CLOSED"
        it["evidence"] = [f"evidence/{pid}-dossier.json"]
        it["waiver_ref"] = ""
    return reg


def write_reg(root, reg):
    p = root / "candidate-register.yaml"
    import yaml
    p.write_text(yaml.safe_dump(reg, allow_unicode=True, sort_keys=False))
    return p


def errors_for(root, reg):
    p = write_reg(root, reg)
    return check(root, "integrity", register=p)


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("合格基线（除签名外全绿）")
def _(root):
    reg = base_register(root)
    errs = errors_for(root, reg)
    # 唯一允许的失败是签名/信任根
    legit = [e for e in errs if "approval" in e.lower() or "trust root" in e.lower() or "closed" not in e.lower()]
    return (len(errs) == 4 and all(("approval" in e.lower() or "trust root" in e.lower()) for e in errs),
            f"errors={errs}")


@case("A1 CLOSED 但 evidence 为空")
def _(root):
    reg = base_register(root)
    reg["items"][0]["evidence"] = []
    errs = errors_for(root, reg)
    return any("dossier" in e for e in errs), f"errors={errs}"


@case("A2 dossier 的 blocker_id 不符")
def _(root):
    reg = base_register(root)
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["blocker_id"] = "P0-02"
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    errs = errors_for(root, reg)
    return any("P0-01" in e and "snapshot" in e or "P0-01" in e and "blocker" in e.lower() for e in errs), f"errors={errs}"


@case("A3 source_snapshot 与当前不一致")
def _(root):
    reg = base_register(root)
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["source_snapshot_sha256"] = "0" * 64
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    return any("snapshot" in e for e in errors_for(root, reg)), ""


@case("A4 少答一项 decision")
def _(root):
    reg = base_register(root)
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["answers"].pop(sorted(d["answers"])[-1])
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    return any("decision items answered" in e for e in errors_for(root, reg)), ""


@case("A5 answer 缺 evidence")
def _(root):
    reg = base_register(root)
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["answers"]["D01"] = {"conclusion": "decided", "evidence": []}
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    return any("conclusion/evidence" in e for e in errors_for(root, reg)), ""


@case("A6 引用证据哈希不符")
def _(root):
    reg = base_register(root)
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["answers"]["D01"]["evidence"][0]["sha256"] = "f" * 64
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    return any("hash mismatch" in e for e in errors_for(root, reg)), ""


@case("A7 引用空文件")
def _(root):
    reg = base_register(root)
    (root / "evidence/P0-01-fact.txt").write_text("")
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["answers"]["D01"]["evidence"][0]["sha256"] = filehash(root / "evidence/P0-01-fact.txt")
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    return any("empty" in e.lower() or "missing" in e.lower() for e in errors_for(root, reg)), ""


@case("A8 verified_tests 全非 PASS")
def _(root):
    reg = base_register(root)
    d = json.loads((root / "evidence/P0-01-dossier.json").read_text())
    d["verified_tests"] = [{"name": "compat", "result": "SKIPPED"}]
    (root / "evidence/P0-01-dossier.json").write_text(json.dumps(d))
    return any("verified successful tests" in e for e in errors_for(root, reg)), ""


@case("A9 无任何 approval")
def _(root):
    reg = base_register(root)
    errs = errors_for(root, reg)
    return any("approval" in e.lower() or "trust root" in e.lower() for e in errs), f"errors={errs[:1]}"


@case("A10 ACCEPTED_RISK 无 waiver_ref")
def _(root):
    reg = base_register(root)
    reg["items"][0]["status"] = "ACCEPTED_RISK"
    return any("accepted risk requires separate waiver" in e for e in errors_for(root, reg)), ""


@case("A11 ACCEPTED_RISK 有 waiver 也不能过 strict")
def _(root):
    import yaml
    reg = base_register(root)
    reg["items"][0]["status"] = "ACCEPTED_RISK"
    reg["items"][0]["waiver_ref"] = "WAIVER-001"
    p = write_reg(root, reg)
    import p0_closure_check as m
    errs = m.check(root, "strict", required=["P0-01"], register=p)
    return any("strict requires CLOSED" in e for e in errs), f"errors={errs[:2]}"


@case("A12 删除一个 P0 项")
def _(root):
    reg = base_register(root)
    reg["items"] = [i for i in reg["items"] if i["id"] != "P0-04"]
    return any("cannot be deleted" in e for e in errors_for(root, reg)), ""


@case("A13 篡改 owner / blocks")
def _(root):
    reg = base_register(root)
    reg["items"][0]["owner"] = "somebody-else"
    return any("owner/impact differs" in e for e in errors_for(root, reg)), ""


def main():
    ok = True
    for name, fn in CASES:
        root = build_root()
        try:
            passed, detail = fn(root)
        except Exception as e:                       # 用例本身崩了也算审计失败
            passed, detail = False, f"exception: {e}"
        mark = "CAUGHT" if passed else "MISSED"
        if not passed:
            ok = False
        print(f"[{mark}] {name}" + (f"  ({detail})" if detail and not passed else ""))
    print("\n结论：", "闸门拦住了全部伪造路径" if ok else "存在未被拦截的伪造路径（见 MISSED）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
