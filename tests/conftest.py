import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FRAMEWORK_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = FRAMEWORK_ROOT / "scripts"


@pytest.fixture
def contract_sandbox(tmp_path):
    """Minimal project root with a runnable real generator + one contract."""
    root = tmp_path / "proj"
    (root / "contracts" / "api").mkdir(parents=True)
    (root / "scripts" / "generators").mkdir(parents=True)
    shutil.copy(
        SCRIPTS / "generators" / "openapi_types.py",
        root / "scripts" / "generators" / "openapi_types.py",
    )
    shutil.copy(
        FRAMEWORK_ROOT / "tests" / "fixtures" / "example-openapi.json",
        root / "contracts" / "api" / "example-openapi.json",
    )
    registry = {
        "registry_version": 1,
        "contracts": [
            {
                "id": "example-api",
                "type": "api",
                "layer": "domain",
                "version": "0.1.0",
                "owner": "tech-lead",
                "path": "api/example-openapi.json",
                "generator": "scripts/generators/openapi_types.py",
                "outputs": ["generated/sdk/example-api.types.json"],
                "depends_on": [],
                "compatibility": "compatible",
            }
        ],
    }
    (root / "contracts" / "registry.yaml").write_text(
        json.dumps(registry, indent=2), encoding="utf-8"
    )
    return root


def run_script(script: str, root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        cwd=str(root),
    )


def write_registry(root: Path, contracts: list[dict]):
    (root / "contracts" / "registry.yaml").write_text(
        json.dumps({"registry_version": 1, "contracts": contracts}, indent=2),
        encoding="utf-8",
    )
