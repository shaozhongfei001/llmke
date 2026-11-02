"""社区报告与 global 端点：可核验的答案，以及"没东西可查不算通过"的引用校验。

前两节测 `global_report`（确定性、fail-closed 引用校验），后两节测 `api` 的
`POST /v2/graph/global` 与 `/health.community`。
"""

import hashlib
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from graph_engine_adapter import global_report  # noqa: E402
from graph_engine_adapter.api import create_app  # noqa: E402

# 两簇互不相连的实体 → 至少 2 个社区（社区按无向连通性做标签传播）
OPENIE = {"docs": [
    {"idx": "c1", "passage": "第一段正文", "extracted_triples": [
        ["北方重工", "额度", "8000万元"],
        ["北方重工", "担保方式", "星航贷"],
        ["星航贷", "担保方式", "保证"],
    ]},
    {"idx": "c2", "passage": "第二段正文", "extracted_triples": [
        ["丙贸易", "额度", "100万元"],
        ["丙贸易", "担保方式", "质押"],
    ]},
]}

SOURCES = {"c1": [{"file_id": "F1", "locator": "page=1", "title": "甲.docx"}],
           "c2": [{"file_id": "F2", "locator": "page=2"}]}


def make_snapshot(tmp_path, *, openie=None, sources=SOURCES, files=("F1", "F2"),
                  name="snapshot-1"):
    snap = tmp_path / name
    snap.mkdir()
    (snap / "openie_results_ner_0.json").write_text(
        json.dumps(openie if openie is not None else OPENIE, ensure_ascii=False), encoding="utf-8")
    if sources is not None:
        (snap / "sources.json").write_text(json.dumps(sources, ensure_ascii=False), encoding="utf-8")
    return snap, list(files)


# ---------- 报告本身 ----------

def test_report_is_deterministic_same_bytes(tmp_path):
    snap1, files = make_snapshot(tmp_path, name="snap-a")
    snap2, _ = make_snapshot(tmp_path, name="snap-b")

    one = global_report.write(str(snap1), files)
    two = global_report.write(str(snap2), files)

    assert one["sha256"] == two["sha256"]
    assert (snap1 / "community.json").read_bytes() == (snap2 / "community.json").read_bytes()
    # 文件里不能有快照路径/时间戳这类每次都会变的东西
    text = (snap1 / "community.json").read_text(encoding="utf-8")
    assert "snap-a" not in text and "snapshot-" not in text


def test_report_contains_members_facts_sources_and_clean_citation_check(tmp_path):
    snap, files = make_snapshot(tmp_path)
    out = global_report.write(str(snap), files)
    report = global_report.load(str(snap))

    assert out["status"] == "READY"
    assert report["community_count"] >= 2

    for section in report["communities"]:
        assert section["entities"], "社区必须有成员"
        assert section["facts"], "社区必须有代表事实"
        for fact in section["facts"]:
            assert fact["sources"], "每条事实都必须带来源"
        assert section["sources"]

    check = report["citation_check"]
    assert check["ok"] is True
    assert check["checked"] > 0              # 真的校验过，不是空集通过
    assert check["invalid"] == []
    assert report["sources_available"] is True

    # 答案逐行带来源
    for line in report["answer"].splitlines():
        assert "（来源：" in line
    assert out["sha256"] == hashlib.sha256(
        (snap / "community.json").read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def test_missing_sources_json_fails_closed(tmp_path):
    """删掉 sources.json：没有引用可校验，但**绝不能**算通过。"""
    snap, files = make_snapshot(tmp_path, sources=None)
    global_report.write(str(snap), files)
    report = global_report.load(str(snap))

    assert report["sources_available"] is False
    assert report["status"] == "BLOCKED"
    assert report["citation_check"]["ok"] is False
    assert report["citation_check"]["reason"] == "SOURCES_MISSING"
    assert report["answer"] == ""


def test_ghost_file_id_in_sources_is_reported_as_invalid(tmp_path):
    """把 sources.json 换成不可见的 file_id：引用校验必须报失效，而不是静默通过。"""
    ghost = {"c1": [{"file_id": "GHOST-1", "locator": "page=1"}],
             "c2": [{"file_id": "GHOST-2", "locator": "page=2"}]}
    snap, _ = make_snapshot(tmp_path, sources=ghost)
    # 本次 build 真正写入的是 F1/F2，幽灵 id 不在里面
    global_report.write(str(snap), ["F1", "F2"])
    report = global_report.load(str(snap))

    assert report["sources_available"] is True
    assert report["status"] == "BLOCKED"
    assert report["citation_check"]["ok"] is False
    assert report["citation_check"]["invalid"], "不可见来源必须落到 invalid 里"
    assert report["answer"] == ""


def test_no_facts_is_not_a_pass(tmp_path):
    snap = tmp_path / "empty"
    snap.mkdir()
    (snap / "openie_results_ner_0.json").write_text('{"docs": []}', encoding="utf-8")
    (snap / "sources.json").write_text("{}", encoding="utf-8")
    global_report.write(str(snap), [])
    report = global_report.load(str(snap))

    assert report["community_count"] == 0
    assert report["citation_check"]["ok"] is False
    assert report["citation_check"]["reason"] == "NO_FACTS"


# ---------- 端点 ----------

class FakeEngine:
    """global 端点只读快照里的 community.json，不需要真的图。"""

    hp = None

    def __init__(self, save_dir):
        self.save_dir = save_dir

    def openie_docs(self):
        return []


def client_for(snapshot):
    return TestClient(create_app(engine_factory=lambda: FakeEngine(str(snapshot))))


def test_global_endpoint_answers_from_report_with_sources(tmp_path):
    snap, files = make_snapshot(tmp_path)
    global_report.write(str(snap), files)

    d = client_for(snap).post("/v2/graph/global", json={"query": "北方重工 额度"}).json()
    assert d["status"] == "READY"
    assert d["communities"] >= 2
    assert d["reason"] is None
    assert d["citation_check"]["ok"] is True

    lines = [ln for ln in d["answer"].splitlines() if ln.strip()]
    assert lines and all("（来源：" in ln for ln in lines)
    assert d["citations"] and all(c["sources"] for c in d["citations"])
    # 社区号必须是真的 id（报告用的键叫 community，不能取成 None）
    assert d["used_communities"]
    assert all(cid and cid.startswith("c-") for cid in d["used_communities"])
    # 报告里的社区成员/事实/来源都能看到（不是只回一段文本）
    assert d["sections"][0]["entities"] and d["sections"][0]["facts"]


def test_global_endpoint_without_report_is_200_with_reason(tmp_path):
    snap, _ = make_snapshot(tmp_path)      # 不写 community.json
    d = client_for(snap).post("/v2/graph/global", json={"query": "x"}).json()

    assert d["communities"] == 0
    assert d["answer"] == "" and d["citations"] == []
    assert d["reason"] == "NO_COMMUNITY_REPORT"
    assert d["citation_check"]["ok"] is False


def test_global_endpoint_withholds_answer_when_citations_invalid(tmp_path):
    ghost = {"c1": [{"file_id": "GHOST-1"}], "c2": [{"file_id": "GHOST-2"}]}
    snap, _ = make_snapshot(tmp_path, sources=ghost)
    global_report.write(str(snap), ["F1", "F2"])

    d = client_for(snap).post("/v2/graph/global", json={"query": "x"}).json()
    assert d["answer"] == "" and d["citations"] == []
    assert d["reason"] == "CITATION_INVALID"
    assert d["citation_check"]["invalid"]


def test_health_reports_community_stats(tmp_path):
    snap, files = make_snapshot(tmp_path)
    written = global_report.write(str(snap), files)

    health = client_for(snap).get("/health").json()
    community = health["community"]
    assert community["wired"] is True
    assert community["communities"] == written["community_count"] >= 2
    assert community["citation_failures"] == 0
    assert community["citation_check_ok"] is True


def test_health_says_not_wired_without_report(tmp_path):
    snap, _ = make_snapshot(tmp_path)
    community = client_for(snap).get("/health").json()["community"]
    assert community["wired"] is False
    assert community["communities"] == 0
    assert community["citation_failures"] is None
