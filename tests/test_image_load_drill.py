"""镜像 load 演练：不真的 docker load（慢且改本机状态），用注入的命令执行器测判定逻辑。

重点不是"能跑"，而是三条安全判定：
- 覆盖了已存在的 tag 必须被识别（不能悄悄顶掉在用镜像）；
- 容器探活失败要如实记录；
- 无论成败都要清理容器。
"""

import importlib.util
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "img_drill", os.path.join(REPO, "scripts", "v2_image_load_drill.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class FakeDocker:
    def __init__(self, before, after, load_out="Loaded image: redis:7.4.10-alpine\n",
                 load_rc=0, ping_ok=True):
        self.before, self.after = before, after
        self.load_out, self.load_rc, self.ping_ok = load_out, load_rc, ping_ok
        self.calls = []
        self._images_calls = 0

    def __call__(self, cmd, timeout=300.0):
        self.calls.append(cmd)
        if cmd[:2] == ["docker", "images"]:
            self._images_calls += 1
            data = self.before if self._images_calls == 1 else self.after
            return 0, "\n".join(f"{k} {v}" for k, v in data.items()) + "\n", ""
        if cmd[:2] == ["docker", "load"]:
            return self.load_rc, "" if self.load_rc else self.load_out, \
                "" if self.load_rc == 0 else "no such file"
        if cmd[:2] == ["docker", "run"]:
            return 0, "abc123\n", ""
        if cmd[:2] == ["docker", "exec"]:
            return (0, "PONG\n", "") if self.ping_ok else (1, "", "connection refused")
        if cmd[:2] == ["docker", "rm"]:
            return 0, "", ""
        return 0, "", ""


def tar(tmp_path):
    p = os.path.join(str(tmp_path), "x.tar")
    with open(p, "wb") as fh:
        fh.write(b"0" * 16)
    return p


def test_new_image_is_not_reported_as_overwrite(tmp_path):
    d = FakeDocker(before={}, after={"redis:7.4.10-alpine": "sha256:new"})
    r = mod.drill(tar(tmp_path), runner=d)
    assert r["image_ref"] == "redis:7.4.10-alpine"
    assert r["overwrote_existing"] is False and r["ok"] is True


def test_same_id_is_idempotent_not_overwrite(tmp_path):
    d = FakeDocker(before={"redis:7.4.10-alpine": "sha256:same"},
                   after={"redis:7.4.10-alpine": "sha256:same"})
    r = mod.drill(tar(tmp_path), runner=d)
    assert r["already_present"] is True
    assert r["overwrote_existing"] is False


def test_different_id_is_flagged_and_old_id_kept(tmp_path):
    d = FakeDocker(before={"redis:7.4.10-alpine": "sha256:old"},
                   after={"redis:7.4.10-alpine": "sha256:new"})
    r = mod.drill(tar(tmp_path), runner=d)
    assert r["overwrote_existing"] is True
    assert r["previous_image_id"] == "sha256:old"
    # 绝不自动删旧镜像：调用记录里不能出现 rmi
    assert not any("rmi" in " ".join(c) for c in d.calls)


def test_container_health_failure_is_reported_and_still_cleaned(tmp_path):
    d = FakeDocker(before={}, after={"redis:7.4.10-alpine": "sha256:new"}, ping_ok=False)
    r = mod.drill(tar(tmp_path), run=True, runner=d)
    assert r["container"]["started"] is True
    assert r["container"]["health_ok"] is False
    assert r["container"]["cleaned_up"] is True
    assert r["ok"] is False


def test_load_failure_returns_error_not_exception(tmp_path):
    d = FakeDocker(before={}, after={}, load_rc=1, load_out="")
    r = mod.drill(tar(tmp_path), runner=d)
    assert r["ok"] is False and r["stage"] == "load"
    assert "no such file" in r["error"]


def test_missing_tar_is_reported(tmp_path):
    r = mod.drill(os.path.join(str(tmp_path), "nope.tar"))
    assert r["ok"] is False and r["error"] == "tar 不存在"


def test_health_ok_path_cleans_up(tmp_path):
    d = FakeDocker(before={}, after={"redis:7.4.10-alpine": "sha256:new"})
    r = mod.drill(tar(tmp_path), run=True, runner=d)
    assert r["container"]["health_ok"] is True
    assert r["container"]["cleaned_up"] is True
    assert r["ok"] is True
