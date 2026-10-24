"""HTTP 入口 × 真库：证明"过滤发生在 SQL"，不是 Python 里的 if。

为什么单独一个文件
    假执行器能测 HTTP 语义，但测不出"越权数据是否真的没被取出来"。
    这条链路的价值恰恰在取数层：`document_chunk` 的授权谓词 + ACTIVE 代次子查询。
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.answer_api.server import make_server
from modules.index_generation import (acquire_lease_sql, activate_seed_sql, insert_guarded_sql,
                                      read_lease_sql)

ROOT = Path(__file__).resolve().parents[1]
SOCKET = Path(os.environ.get("LLMKE_MYSQL_SOCKET", "/tmp/mysql-probe/mysql.sock"))
MYSQL = shutil.which("mysql")
SCHEMA = ROOT / "docs/baseline/validation/artifacts/schema-v1.3.sql"
DB = os.environ.get("LLMKE_CI_SERVER_DB", "llmke_ci_server")

DOC = "第一段内容。第二段内容。"
FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
LOCS = {"vector": "v", "es": "e", "graph": "g", "fulltext": "f"}

pytestmark = pytest.mark.skipif(
    MYSQL is None or not SOCKET.exists(),
    reason="需要本机 MySQL 独立实例（coordination/mysql-probe.sh start）与 mysql 客户端",
)


def run(statement: str, *, database: str | None = DB) -> tuple[str, int]:
    cmd = [MYSQL, f"--socket={SOCKET}", "-uroot", "-N", "-B"]
    if database:
        cmd.insert(3, database)
    p = subprocess.run(cmd, input=f"{statement};\nSELECT ROW_COUNT();\n",
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError(f"SQL 失败: {statement[:90]}...\n{p.stderr.strip()}")
    lines = p.stdout.rstrip("\n").split("\n") if p.stdout.strip() else []
    affected = int(lines[-1]) if lines and lines[-1].lstrip("-").isdigit() else 0
    return "\n".join(lines[:-1]), affected


def runner(sql: str) -> list[list[str]]:
    p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", "-N", "-B", DB],
                       input=sql + ";\n", capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise AssertionError(f"SELECT 失败: {p.stderr.strip()}")
    return [line.split("\t") for line in p.stdout.splitlines() if line]


def headers(files, kb="kb-1"):
    return {'X-Request-Id': 'req-db', 'X-Principal-Id': 'user-1', 'X-Service': 'answer',
            'X-Kb-Scope': kb, 'X-File-Scope': json.dumps({kb: files}),
            'X-Authz-Version': '1', 'X-Expires-At': FUTURE}


@pytest.fixture(scope="module")
def db():
    run("SELECT 1", database=None)
    run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)
    run(f"CREATE DATABASE `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci", database=None)
    with SCHEMA.open("rb") as fh:
        p = subprocess.run([MYSQL, f"--socket={SOCKET}", "-uroot", DB],
                           stdin=fh, capture_output=True, timeout=120)
    assert p.returncode == 0, p.stderr.decode()[:400]

    content = hashlib.sha256(DOC.encode()).hexdigest()
    run("INSERT INTO index_generation (kb_id,content_hash,document_version,parse_version,"
        "chunk_version,embedding_version,physical_locations,manifest_json,state,created_at,created_by) "
        f"VALUES ('kb-1','{content}','v1','p1','c1','e1','{json.dumps(LOCS)}','{{}}','BUILDING',NOW(3),'ci')")
    gid = int(run("SELECT generation_id FROM index_generation WHERE kb_id='kb-1'")[0].strip())
    run(f"UPDATE index_generation SET state='ACTIVE' WHERE generation_id={gid}")
    run(activate_seed_sql("kb-1", gid, "ci"))
    upd, ins = acquire_lease_sql("kb-1", gid, "worker-1", 60)
    if run(upd)[1] == 0:
        run(ins)
    lease = int(run(read_lease_sql("kb-1", gid))[0].split("\t")[0])

    cols = ["chunk_id", "kb_id", "file_id", "document_version", "chunk_index", "offset_start",
            "offset_end", "offset_unit", "text", "text_hash", "content_hash", "parser_version",
            "chunk_strategy", "created_at", "created_by"]
    for cid, fid, idx, s, e in (("k1", "f-1", 0, 0, 6), ("k2", "f-2", 1, 6, 12)):
        text = DOC[s:e]
        values = (f"'{cid}','kb-1','{fid}','v1',{idx},{s},{e},'unicode_codepoint','{text}',"
                  f"'{hashlib.sha256(text.encode()).hexdigest()}','{content}','p-1','S1',NOW(3),'ci'")
        assert run(insert_guarded_sql("kb-1", gid, lease, "document_chunk", cols, values))[1] == 1
    try:
        yield {"gid": gid}
    finally:
        run(f"DROP DATABASE IF EXISTS `{DB}`", database=None)


@pytest.fixture()
def server(db):
    srv = make_server(runner, port=0, audit=lambda _l: None)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv
    srv.shutdown()
    srv.server_close()


def post(srv, payload, hs):
    c = http.client.HTTPConnection('127.0.0.1', srv.server_port, timeout=10)
    c.request('POST', '/answer', json.dumps(payload).encode(),
              {'Content-Type': 'application/json', **hs})
    r = c.getresponse()
    raw = r.read()
    c.close()
    return r.status, json.loads(raw or b'{}')


def test_http_only_sees_authorized_file(server):
    status, body = post(server, {'query': '第一段', 'kb_id': 'kb-1',
                                 'document_texts': {'f-1': DOC, 'f-2': DOC}}, headers(['f-1']))
    assert status == 200, body
    assert {c['file_id'] for c in body['data']['citations']} == {'f-1'}
    assert '第二段内容' not in body['data']['answer']['text']


def test_http_other_file_authorization(server):
    status, body = post(server, {'query': '第二段', 'kb_id': 'kb-1',
                                 'document_texts': {'f-1': DOC, 'f-2': DOC}}, headers(['f-2']))
    assert status == 200, body
    assert {c['file_id'] for c in body['data']['citations']} == {'f-2'}


def test_http_index_not_ready_after_deactivation(server, db):
    run("DELETE FROM index_generation_activation WHERE kb_id='kb-1'")
    status, body = post(server, {'query': '第一段', 'kb_id': 'kb-1',
                                 'document_texts': {'f-1': DOC}}, headers(['f-1']))
    assert status == 503, body
    assert body['error']['code'] == 'INDEX_NOT_READY'
    run(activate_seed_sql("kb-1", db["gid"], "ci"))
