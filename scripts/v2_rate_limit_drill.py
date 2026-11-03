#!/usr/bin/env python
"""限流真跑：起一个假的 OpenAI 兼容服务，用真实 `make_llm_call` 打它。

为什么不用 mock 掉 urlopen：限流要证明的是"**调用被拦在发请求之前**"。
如果 mock 了传输层，就分不清"没发出去"和"发出去了但被本地逻辑丢弃"——
这两种在真实故障里后果完全不同（前者不花钱、后者照样计费）。

三种场景：
1. 不配 `LLMKE_ANSWER_RATE` → 3 次调用全过（原有行为不变）；
2. 配 `2/60` → 前 2 次过，第 3 次抛 RateLimitedError，且服务端只收到 2 次请求；
3. `describe()` 不含密钥明文。
"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "services/rag-alg/index_data_service"))


def start_server():
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            hits.append(self.rfile.read(length))
            body = json.dumps({"choices": [{"message": {"content": "好的"},
                                            "finish_reason": "stop"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, hits


def run_calls(cfg, count):
    from graph_engine_adapter.llm_config import make_llm_call
    from graph_engine_adapter.llm_budget import RateLimitedError

    call = make_llm_call(cfg)
    ok, denied = 0, []
    for index in range(count):
        try:
            call([{"role": "user", "content": f"问题{index}"}])
            ok += 1
        except RateLimitedError as exc:
            denied.append({"index": index, "retry_after": getattr(exc, "retry_after", None),
                           "message": str(exc)[:80]})
    return {"ok": ok, "denied": denied}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", type=int, default=3)
    ap.add_argument("--rate", default="2/60")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    from graph_engine_adapter.llm_config import describe, resolve

    server, hits = start_server()
    base = f"http://127.0.0.1:{server.server_port}/v1"
    env_base = {"LLMKE_ANSWER_PROVIDER": "deepseek", "LLMKE_ANSWER_API_BASE": base,
                "LLMKE_ANSWER_KEY_ENV": "DRILL_KEY", "DRILL_KEY": "sk-drill-secret"}
    problems, report = [], {}

    try:
        # 1) 不配限流：全过
        free = resolve(dict(env_base))
        before = len(hits)
        free_result = run_calls(free, args.calls)
        report["unlimited"] = {**free_result, "server_hits": len(hits) - before}
        if free_result["ok"] != args.calls or free_result["denied"]:
            problems.append(f"未配限流时被拦：{free_result}")
        if len(hits) - before != args.calls:
            problems.append("未配限流时请求数不符")

        # 2) 配 2/60：前 2 过、第 3 被拦，服务端只该收到 2 次
        limited = resolve({**env_base, "LLMKE_ANSWER_RATE": args.rate})
        before = len(hits)
        limited_result = run_calls(limited, args.calls)
        # 只序列化 stats()：把 CallBudget 对象直接塞进 report 会让 json.dump 中途抛错，
        # 留下**截断的半个文件**，读取方拿到的是"文件存在但解析失败"——比没有文件更难查。
        budget_stats = limited["budget"].stats() if limited.get("budget") else None
        report["limited"] = {**limited_result, "server_hits": len(hits) - before,
                             "budget": budget_stats}
        if limited_result["ok"] != 2:
            problems.append(f"配 {args.rate} 后通过数应为 2，实际 {limited_result['ok']}")
        if len(limited_result["denied"]) != args.calls - 2:
            problems.append("超限未被拦")
        if len(hits) - before != 2:
            problems.append(f"超限请求仍打到服务端（{len(hits) - before} 次），限流没有拦在发送前")
        retry_after = (limited_result["denied"] or [{}])[0].get("retry_after")
        if not retry_after or retry_after <= 0:
            problems.append(f"retry_after 不合理：{retry_after}")

        # 3) describe 不泄密
        desc = describe(limited)
        report["describe"] = desc
        dumped = json.dumps(desc, ensure_ascii=False)
        if "sk-drill-secret" in dumped:
            problems.append("describe() 泄露了密钥明文")
    finally:
        server.shutdown()

    report["status"] = "OK" if not problems else "FAIL"
    report["problems"] = problems
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"status": report["status"], "problems": problems,
                      "unlimited": report["unlimited"]["ok"],
                      "limited": report["limited"]["ok"],
                      "server_hits": report["limited"]["server_hits"]}, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
