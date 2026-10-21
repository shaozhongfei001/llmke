"""P0-01 / P1-01 / P1-02 — contract toolchain fail-closed tests."""
import json
from pathlib import Path

from conftest import run_script, write_registry


def _gen(root):
    return run_script("contract_generate.py", root)


def _check(root):
    return run_script("contract_check.py", root)


def test_real_generate_and_check_pass(contract_sandbox):
    g = _gen(contract_sandbox)
    assert g.returncode == 0, g.stdout + g.stderr
    out = contract_sandbox / "generated" / "sdk" / "example-api.types.json"
    assert out.is_file() and out.stat().st_size > 0
    report = json.loads(
        (contract_sandbox / "contracts" / "build" / "generate-report.json").read_text()
    )
    entry = report["contracts"][0]
    assert entry["input_sha256"]
    assert entry["outputs"]["generated/sdk/example-api.types.json"]
    c = _check(contract_sandbox)
    assert c.returncode == 0, c.stdout + c.stderr
    assert (contract_sandbox / "contracts" / "build" / "check-report.json").is_file()


def test_missing_generator_fails(contract_sandbox):
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["generator"] = "scripts/generators/does-not-exist.py"
    write_registry(contract_sandbox, reg["contracts"])
    r = _gen(contract_sandbox)
    assert r.returncode != 0
    assert "MISSING_OR_DUMMY_GENERATOR" in r.stdout


def test_missing_checker_fails(contract_sandbox):
    assert _gen(contract_sandbox).returncode == 0
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["checker"] = "scripts/checkers/nope.py"
    write_registry(contract_sandbox, reg["contracts"])
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "MISSING_OR_DUMMY_CHECKER" in r.stdout


def test_dummy_generator_fails(contract_sandbox):
    dummy = contract_sandbox / "scripts" / "generators" / "dummy.py"
    dummy.write_text("# TODO: implement real generator\nprint('PASS')\n")
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["generator"] = "scripts/generators/dummy.py"
    write_registry(contract_sandbox, reg["contracts"])
    r = _gen(contract_sandbox)
    assert r.returncode != 0
    assert "MISSING_OR_DUMMY_GENERATOR" in r.stdout


def test_noop_generator_fails(contract_sandbox):
    noop = contract_sandbox / "scripts" / "generators" / "noop.py"
    noop.write_text("print('generated nothing but exits 0')\n")
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["generator"] = "scripts/generators/noop.py"
    write_registry(contract_sandbox, reg["contracts"])
    r = _gen(contract_sandbox)
    assert r.returncode != 0
    assert "EMPTY_OUTPUT" in r.stdout


def test_empty_output_fails(contract_sandbox):
    empty_maker = contract_sandbox / "scripts" / "generators" / "empty.py"
    empty_maker.write_text(
        "import argparse, pathlib\n"
        "ap = argparse.ArgumentParser()\n"
        "ap.add_argument('--contract'); ap.add_argument('--outdir'); ap.add_argument('--id')\n"
        "a = ap.parse_args()\n"
        "p = pathlib.Path(a.outdir) / 'generated' / 'sdk' / (a.id + '.types.json')\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_text('')\n"
    )
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["generator"] = "scripts/generators/empty.py"
    write_registry(contract_sandbox, reg["contracts"])
    r = _gen(contract_sandbox)
    assert r.returncode != 0
    assert "EMPTY_OUTPUT" in r.stdout


def test_unregistered_contract_fails(contract_sandbox):
    (contract_sandbox / "contracts" / "api" / "rogue.json").write_text(
        '{"openapi": "3.0.3", "info": {"title": "x", "version": "1.0.0"}, "paths": {}}'
    )
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "UNREGISTERED_CONTRACT" in r.stdout


def test_duplicate_id_fails(contract_sandbox):
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"].append(dict(reg["contracts"][0]))
    write_registry(contract_sandbox, reg["contracts"])
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "DUPLICATE_ID" in r.stdout


def test_cyclic_dependency_fails(contract_sandbox):
    (contract_sandbox / "contracts" / "api" / "b.json").write_text(
        '{"openapi": "3.0.3", "info": {"title": "b", "version": "1.0.0"}, "paths": {}}'
    )
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    a = reg["contracts"][0]
    a["depends_on"] = ["b-api"]
    b = dict(a)
    b.update({"id": "b-api", "path": "api/b.json", "depends_on": ["example-api"],
              "generator": "", "outputs": []})
    write_registry(contract_sandbox, [a, b])
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "cycle" in r.stdout.lower()


def test_dead_dependency_reference_fails(contract_sandbox):
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["depends_on"] = ["ghost"]
    write_registry(contract_sandbox, reg["contracts"])
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "unknown id" in r.stdout


def test_bad_version_fails(contract_sandbox):
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["version"] = "latest"
    write_registry(contract_sandbox, reg["contracts"])
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "semver" in r.stdout


def test_drift_after_contract_change_fails(contract_sandbox):
    assert _gen(contract_sandbox).returncode == 0
    cpath = contract_sandbox / "contracts" / "api" / "example-openapi.json"
    doc = json.loads(cpath.read_text())
    doc["info"]["version"] = "0.2.0"
    cpath.write_text(json.dumps(doc, indent=2))
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "DRIFT" in r.stdout


def test_tampered_generated_output_fails(contract_sandbox):
    assert _gen(contract_sandbox).returncode == 0
    out = contract_sandbox / "generated" / "sdk" / "example-api.types.json"
    out.write_text('{"tampered": true}\n')
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "LINKAGE" in r.stdout


def test_domain_layer_ui_binding_fails(contract_sandbox):
    cpath = contract_sandbox / "contracts" / "api" / "example-openapi.json"
    doc = json.loads(cpath.read_text())
    doc["components"]["schemas"]["Chart"] = {
        "type": "object",
        "properties": {"echarts_option": {"type": "object"}},
    }
    cpath.write_text(json.dumps(doc, indent=2))
    assert _gen(contract_sandbox).returncode == 0
    r = _check(contract_sandbox)
    assert r.returncode != 0
    assert "LAYERING" in r.stdout


def test_bff_layer_ui_binding_passes(contract_sandbox):
    cpath = contract_sandbox / "contracts" / "api" / "example-openapi.json"
    doc = json.loads(cpath.read_text())
    doc["components"]["schemas"]["Chart"] = {
        "type": "object",
        "properties": {"echarts_option": {"type": "object"}},
    }
    cpath.write_text(json.dumps(doc, indent=2))
    reg = json.loads((contract_sandbox / "contracts" / "registry.yaml").read_text())
    reg["contracts"][0]["layer"] = "bff"
    write_registry(contract_sandbox, reg["contracts"])
    assert _gen(contract_sandbox).returncode == 0
    r = _check(contract_sandbox)
    assert r.returncode == 0, r.stdout + r.stderr


def test_duplicate_registry_key_fails(contract_sandbox):
    p = contract_sandbox / "contracts" / "registry.yaml"
    p.write_text('{"registry_version":1,"registry_version":1,"contracts":[]}')
    r = _check(contract_sandbox)
    assert r.returncode != 0 and "duplicate" in r.stdout.lower()
