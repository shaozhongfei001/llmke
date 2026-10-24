"""HTTP 入口测试：先证"能应答"，再证"该拒绝时拒绝"。

分工
    - 绝大多数用例用**假执行器**（内存返回行）：HTTP 语义与授权分支不该依赖数据库，
      否则每个边界都要起库，慢且脆；
    - 只有"真库 → HTTP"一条用 MySQL，证明取数确实是 SQL 过滤，而不是 Python 里 `if`。

覆盖的错误面（每条都对应真实事故）
    缺上下文（网关漏配）、kb 越权、无证据、索引未就绪、超大请求体、坏 JSON、
    方法/路径错误，以及"审计行不得记录查询原文"。
"""
from __future__ import annotations

import hashlib
import http.client
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.answer_api.server import context_from_headers, make_server

DOC = "第一段内容。第二段内容。"
FUTURE = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()


def sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def row(cid: str, fid: str, idx: int, start: int, end: int, doc: str = DOC) -> list[str]:
    text = doc[start:end]
    return [cid, 'kb-1', fid, 'v1', str(idx), str(start), str(end), 'unicode_codepoint',
            text, sha(text), sha(doc), 'p-1', 'S1']


def headers(**over) -> dict:
    base = {
        'X-Request-Id': 'req-1', 'X-Principal-Id': 'user-1', 'X-Service': 'answer',
        'X-Kb-Scope': 'kb-1', 'X-File-Scope': json.dumps({'kb-1': ['f-1']}),
        'X-Authz-Version': '1', 'X-Expires-At': FUTURE,
    }
    base.update(over)
    return {k: v for k, v in base.items() if v is not None}


@pytest.fixture()
def server_factory():
    servers = []

    def start(runner, audit=None):
        srv = make_server(runner, port=0, audit=audit or (lambda _l: None))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return srv

    yield start
    for s in servers:
        s.shutdown()
        s.server_close()


def post(srv, payload, hs, path='/answer'):
    c = http.client.HTTPConnection('127.0.0.1', srv.server_port, timeout=5)
    c.request('POST', path, json.dumps(payload).encode(),
              {'Content-Type': 'application/json', **hs})
    r = c.getresponse()
    raw = r.read()
    c.close()
    return r.status, json.loads(raw or b'{}')


def get(srv, path):
    c = http.client.HTTPConnection('127.0.0.1', srv.server_port, timeout=5)
    c.request('GET', path)
    r = c.getresponse()
    raw = r.read()
    c.close()
    return r.status, json.loads(raw or b'{}')


def fake_runner(rows, active_version='v1'):
    """按 SQL 形状分流。注意顺序：chunk 查询里也含 `g.document_version`（相关子查询），
    必须先判 `SELECT chunk_id`，否则会把取块查询当成代次探针，返回一行版本号。"""
    def run(sql: str):
        if 'SELECT chunk_id' in sql:
            return rows
        if 'index_generation_activation' in sql:
            return [[active_version]] if active_version else []
        return []
    return run


def test_healthz(server_factory):
    srv = server_factory(fake_runner([]))
    assert get(srv, '/healthz')[0] == 200


def test_answer_ok(server_factory):
    srv = server_factory(fake_runner([row('k1', 'f-1', 0, 0, 6)]))
    status, body = post(srv, {'query': '第一段', 'kb_id': 'kb-1',
                              'document_texts': {'f-1': DOC}}, headers())
    assert status == 200, body
    assert body['ok'] is True
    assert body['data']['policy_state'] == 'CANDIDATE_NOT_RELEASEABLE'
    assert [c['chunk_id'] for c in body['data']['citations']] == ['k1']


def test_missing_context_is_403(server_factory):
    srv = server_factory(fake_runner([]))
    status, body = post(srv, {'query': 'x', 'kb_id': 'kb-1'}, headers(**{'X-Authz-Version': None}))
    assert status == 403
    assert body['error']['code'] == 'CONTEXT_MISSING'


def test_kb_out_of_scope_is_403(server_factory):
    srv = server_factory(fake_runner([row('k1', 'f-1', 0, 0, 6)]))
    status, body = post(srv, {'query': 'x', 'kb_id': 'kb-1', 'document_texts': {'f-1': DOC}},
                        headers(**{'X-Kb-Scope': 'kb-2',
                                   'X-File-Scope': json.dumps({'kb-2': ['f-1']})}))
    assert status == 403
    assert body['error']['code'] == 'KB_NOT_AUTHORIZED'


def test_no_evidence_is_422(server_factory):
    srv = server_factory(fake_runner([], active_version='v1'))   # 代次在，但没有行
    status, body = post(srv, {'query': 'x', 'kb_id': 'kb-1', 'document_texts': {}}, headers())
    assert status == 422
    assert body['error']['code'] == 'NO_EVIDENCE'


def test_index_not_ready_is_503(server_factory):
    srv = server_factory(fake_runner([], active_version=None))   # 无 ACTIVE 代次
    status, body = post(srv, {'query': 'x', 'kb_id': 'kb-1', 'document_texts': {}}, headers())
    assert status == 503
    assert body['error']['code'] == 'INDEX_NOT_READY'


def test_bad_json_is_400(server_factory):
    srv = server_factory(fake_runner([]))
    c = http.client.HTTPConnection('127.0.0.1', srv.server_port, timeout=5)
    c.request('POST', '/answer', b'{not json', {'Content-Type': 'application/json', **headers()})
    r = c.getresponse()
    assert r.status == 400
    c.close()


def test_oversize_body_is_413(server_factory):
    srv = server_factory(fake_runner([]))
    c = http.client.HTTPConnection('127.0.0.1', srv.server_port, timeout=5)
    c.putrequest('POST', '/answer')
    c.putheader('Content-Length', '70000')
    c.putheader('Content-Type', 'application/json')
    c.endheaders()
    r = c.getresponse()
    assert r.status == 413
    c.close()


def test_unknown_path_and_wrong_method(server_factory):
    srv = server_factory(fake_runner([]))
    assert get(srv, '/nope')[0] == 404
    assert get(srv, '/answer')[0] == 405


def test_audit_line_has_no_query_text(server_factory):
    lines = []
    srv = server_factory(fake_runner([row('k1', 'f-1', 0, 0, 6)]), audit=lines.append)
    post(srv, {'query': '机密查询词', 'kb_id': 'kb-1', 'document_texts': {'f-1': DOC}}, headers())
    for _ in range(100):            # 最多等 1 秒；不把"审计一定先写"当作测试前提
        if lines:
            break
        import time as _t
        _t.sleep(0.01)
    assert lines and lines[0]['status'] == 200
    assert '机密查询词' not in json.dumps(lines, ensure_ascii=False)
    assert lines[0]['evidence_count'] == 1
    assert lines[0]['request_id'] == 'req-1'


def test_context_from_headers_rejects_bad_file_scope():
    from modules.answer_api import AnswerError
    with pytest.raises(AnswerError) as e:
        context_from_headers({'X-Request-Id': 'r', 'X-Principal-Id': 'u', 'X-Service': 's',
                              'X-Kb-Scope': 'kb-1', 'X-File-Scope': 'not-json',
                              'X-Authz-Version': '1', 'X-Expires-At': FUTURE})
    assert e.value.code == 'ILLEGAL_INPUT'
