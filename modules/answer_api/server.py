"""HTTP 入口：把答案链暴露成可以被真实请求调用的服务。

为什么需要这一层
    `modules/answer_api` 之前只能被测试调用（`build_answer` 是纯函数，CLI 读文件）。
    真实请求进不来，等于这条链没有"入口"。本层补的就是最后一段：
    HTTP → 授权上下文 → 取块（ACTIVE 代次）→ 证据 → 答案 → 状态码 + 审计行。

只依赖标准库
    `http.server` 足以承担"可运行 + 可测"，不引入框架依赖（requirements.lock 属控制面，
    本轮不动）。将来换框架时，业务函数与状态码表不变。

安全边界（必须写清，否则会被误读成生产鉴权）
    1. 授权上下文来自网关注入的请求头（`X-Authz-*`）。**本层不做身份认证**：
       它只校验上下文的结构与时效，并据此过滤数据。生产上这些头必须由受信网关签发，
       客户端直连必须被网络层挡住。
    2. 未提供上下文 → 直接拒绝（fail-closed），不按"空权限"继续。
    3. 响应恒带 `policy_state=CANDIDATE_NOT_RELEASEABLE`（E1 规范未批准）。
    4. 审计行**不记录查询原文**（可能含业务敏感信息），只记 id/主体/范围/状态/耗时。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlparse

from modules.answer_api.service import AnswerError, build_answer, to_api_error
from modules.answer_api.sql_adapter import fetch_chunks_active
from modules.authz.context import AuthZError

MAX_BODY = 64 * 1024
Runner = Callable[[str], list[list[str]]]

# 网关上下文头的映射：缺任何一个都拒绝
HEADER_MAP = {
    'request_id': 'X-Request-Id',
    'principal_id': 'X-Principal-Id',
    'service': 'X-Service',
    'kb_scope': 'X-Kb-Scope',
    'file_scope': 'X-File-Scope',
    'authz_version': 'X-Authz-Version',
    'expires_at': 'X-Expires-At',
}

# 授权类错误 → 403；其余交给统一状态码表
AUTHZ_CODES = {'CONTEXT_MISSING', 'FIELD_MISSING', 'KB_SCOPE_EMPTY', 'FILE_SCOPE_EMPTY',
               'KB_NOT_AUTHORIZED', 'KB_SCOPE_MISSING', 'CHUNK_OUT_OF_SCOPE',
               'CONTEXT_EXPIRED', 'BAD_VERSION', 'BAD_TIMESTAMP', 'BAD_KB_ID', 'BAD_FILE_ID'}


def context_from_headers(headers: dict) -> dict:
    """从请求头构造授权上下文；缺字段直接抛 `AnswerError('CONTEXT_MISSING')`。

    `headers` 用 `email.message.Message` 亦可（大小写不敏感）；这里统一取 `.get()`。
    """
    raw = {}
    for field, name in HEADER_MAP.items():
        value = headers.get(name)
        if value is None or str(value).strip() == '':
            raise AnswerError('CONTEXT_MISSING', f'缺少 {name}')
        raw[field] = str(value).strip()

    try:
        file_scope = json.loads(raw['file_scope'])
    except json.JSONDecodeError as e:
        raise AnswerError('ILLEGAL_INPUT', f'X-File-Scope 不是合法 JSON: {e.msg}') from e
    if not isinstance(file_scope, dict):
        raise AnswerError('ILLEGAL_INPUT', 'X-File-Scope 必须是对象')

    kb_scope = [k.strip() for k in raw['kb_scope'].split(',') if k.strip()]
    try:
        version = int(raw['authz_version'])
    except ValueError as e:
        raise AnswerError('BAD_VERSION', raw['authz_version']) from e

    return {'request_id': raw['request_id'], 'principal_id': raw['principal_id'],
            'service': raw['service'], 'kb_scope': kb_scope, 'file_scope': file_scope,
            'authz_version': version, 'expires_at': raw['expires_at']}


def answer_request(runner: Runner, payload: dict, headers: dict) -> tuple[int, dict]:
    """一次业务请求 → (状态码, 响应体)。所有异常都在这里收敛，不外泄栈。"""
    try:
        ctx = context_from_headers(headers)
        kb_id = payload.get('kb_id')
        if not isinstance(kb_id, str) or not kb_id:
            raise AnswerError('ILLEGAL_INPUT', 'kb_id 必填')
        query = payload.get('query')
        if not isinstance(query, str) or not query.strip():
            raise AnswerError('QUERY_EMPTY', '查询为空')

        chunks, _sql = fetch_chunks_active(runner, ctx, kb_id, limit=int(payload.get('limit', 20)))
        result = build_answer(query, ctx, kb_id, chunks,
                              payload.get('document_texts') or {},
                              rank=bool(payload.get('rank', False)),
                              min_relevance=float(payload.get('min_relevance', 0.0)),
                              top_k=payload.get('top_k'))
    except (AnswerError, AuthZError) as e:
        code = getattr(e, 'code', 'INTERNAL')
        status = 403 if code in AUTHZ_CODES else _status(code)
        return status, to_api_error(e)
    except Exception as exc:               # noqa: BLE001 —— 兜底不外泄
        # 客户端只看到 INTERNAL；服务端留一行"异常类型"（不含消息与栈），
        # 否则 500 变成无法排查的黑洞（本次就因此多花了一轮定位）。
        sys.stderr.write(f'[answer] internal error: {type(exc).__name__}\n')
        sys.stderr.flush()
        return 500, {'ok': False, 'error': {'code': 'INTERNAL', 'message': '内部错误'}}
    return 200, {'ok': True, 'data': result}


def _status(code: str) -> int:
    from modules.answer_api.handler import STATUS_BY_CODE
    return STATUS_BY_CODE.get(code, 500)


def _audit(line: dict) -> None:
    """审计行写 stderr：一行一个 JSON，便于采集；不含查询原文与正文。"""
    sys.stderr.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + '\n')
    sys.stderr.flush()


def make_server(runner: Runner, host: str = '127.0.0.1', port: int = 0,
                audit: Callable[[dict], None] = _audit) -> ThreadingHTTPServer:
    """构造服务器；port=0 时由系统分配（测试用），实际端口见 `server.server_port`。"""

    class Handler(BaseHTTPRequestHandler):
        server_version = 'llmke-answer/1'
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *args):      # 默认日志会写客户端地址，改由审计行承担
            return

        def _send(self, status: int, body: dict) -> None:
            raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):                        # noqa: N802
            if urlparse(self.path).path == '/healthz':
                return self._send(200, {'ok': True, 'data': {'status': 'ok'}})
            if urlparse(self.path).path == '/answer':
                return self._send(405, {'ok': False, 'error': {'code': 'METHOD_NOT_ALLOWED',
                                                               'message': '请用 POST'}})
            return self._send(404, {'ok': False, 'error': {'code': 'NOT_FOUND',
                                                           'message': '未知路径'}})

        def do_POST(self):                       # noqa: N802
            if urlparse(self.path).path != '/answer':
                return self._send(404, {'ok': False, 'error': {'code': 'NOT_FOUND',
                                                               'message': '未知路径'}})
            started = time.monotonic()
            length = int(self.headers.get('Content-Length') or 0)
            if length > MAX_BODY:
                return self._send(413, {'ok': False, 'error': {'code': 'BODY_TOO_LARGE',
                                                               'message': f'> {MAX_BODY} 字节'}})
            try:
                payload = json.loads(self.rfile.read(length) or b'{}')
            except json.JSONDecodeError:
                return self._send(400, {'ok': False, 'error': {'code': 'ILLEGAL_INPUT',
                                                               'message': '请求体不是合法 JSON'}})
            if not isinstance(payload, dict):
                return self._send(400, {'ok': False, 'error': {'code': 'ILLEGAL_INPUT',
                                                               'message': '请求体必须是对象'}})

            status, body = answer_request(runner, payload, self.headers)

            # 审计**先于**响应落盘：否则客户端可能在审计行写出前就返回，
            # 既让测试出现竞态，也可能在崩溃时留下"有响应、无审计"的空洞。
            # 代价：若随后发送失败（客户端断开），审计记的是"已生成响应"而非"已送达"，
            # 这一点在字段语义上按 status 表示"服务端判定结果"，不宣称送达。
            data = body.get('data') or {}
            audit({'at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'path': '/answer',
                   'status': status,
                   'code': (body.get('error') or {}).get('code'),
                   'request_id': self.headers.get('X-Request-Id'),
                   'principal_id': self.headers.get('X-Principal-Id'),
                   'kb_id': payload.get('kb_id'),
                   'evidence_count': len(data.get('citations') or []),
                   'elapsed_ms': round((time.monotonic() - started) * 1000, 2)})
            self._send(status, body)

    return ThreadingHTTPServer((host, port), Handler)


# `make_server` 的名字在测试里被 import；runner 通过闭包传入
def serve(runner: Runner, host: str, port: int) -> None:
    srv = make_server(runner, host, port)
    print(f'listening on http://{host}:{srv.server_port}', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='answer_api.server')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--mysql-socket', default='/tmp/mysql-probe/mysql.sock')
    ap.add_argument('--database', default='llmke_answer')
    a = ap.parse_args(argv)

    import subprocess

    def runner(sql: str) -> list[list[str]]:
        p = subprocess.run(['mysql', f'--socket={a.mysql_socket}', '-uroot', '-N', '-B', a.database],
                           input=sql + ';\n', capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            raise AnswerError('INDEX_NOT_READY', f'DB 查询失败: {p.stderr.strip()[:120]}')
        return [line.split('\t') for line in p.stdout.splitlines() if line]

    serve(runner, a.host, a.port)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
