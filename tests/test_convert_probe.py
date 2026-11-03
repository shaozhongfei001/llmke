"""转换能力探测：必须能把"没装"与"装了但缺 Writer"分开，否则修错方向。

用假的 soffice 脚本注入 PATH，验证分类逻辑；不依赖本机是否真的装了 LibreOffice。
"""

import importlib.util
import json
import os
import stat

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "v2_convert_probe", os.path.join(REPO, "scripts", "v2_convert_probe.py"))
probe_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe_mod)


def make_fake_soffice(bindir, *, succeeds):
    path = bindir / "soffice"
    if succeeds:
        body = f'''#!/bin/sh
out=""
prev=""
for a in "$@"; do
  if [ "$prev" = "--outdir" ]; then out="$a"; fi
  prev="$a"
done
printf '%%PDF-1.4 fake' > "$out/input.pdf"
exit 0
'''
    else:
        body = '#!/bin/sh\necho "Error: source file could not be loaded" >&2\nexit 1\n'
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_no_soffice_in_path(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    out = probe_mod.probe()
    assert out["status"] == "NO_SOFFICE"


def test_missing_source(tmp_path, monkeypatch):
    make_fake_soffice(tmp_path, succeeds=True)
    monkeypatch.setenv("PATH", str(tmp_path))
    out = probe_mod.probe(source=str(tmp_path / "nope.docx"))
    assert out["status"] == "NO_SOURCE"


def test_success_path_reports_pdf_bytes(tmp_path, monkeypatch):
    make_fake_soffice(tmp_path, succeeds=True)
    monkeypatch.setenv("PATH", str(tmp_path))
    src = tmp_path / "a.docx"
    src.write_bytes(b"fake docx")
    out = probe_mod.probe(source=str(src))
    assert out["status"] == "OK"
    assert out["pdf_bytes"] > 0


def test_failure_without_writer_lib_is_attributed_to_writer(tmp_path, monkeypatch):
    """关键分类：soffice 在但没 libswlo.so → NO_WRITER_FILTER（不是笼统的"转换失败"）。"""
    make_fake_soffice(tmp_path, succeeds=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    src = tmp_path / "a.docx"
    src.write_bytes(b"fake docx")
    out = probe_mod.probe(source=str(src))
    assert out["status"] == "NO_WRITER_FILTER"
    assert "libswlo.so" in out["detail"]


def test_writer_libs_returns_list():
    assert isinstance(probe_mod.writer_libs(None), list)
