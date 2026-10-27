#!/usr/bin/env python3
"""负向回归：摘要存储不可用时，global/local 必须返回 500，**不能伪装成拒答**。

背景（F 13:10 实测）：ES 重启窗口里 `_load_summaries()` 读失败，
旧实现 `return []` → `query_community` 把它当成"这个库没有社区摘要" →
返回 200 + "现有社区摘要不足以回答"。用户看到的是"答不了"，实际是故障。

本用例把 ES 端口指向一个必然连不上的端口，断言：
  ① code == 500
  ② msg 明确说"读取失败/不可用"
  ③ data.error == "summary_store_unavailable"
  ④ **global 与 local 两种 mode 都要满足**（不能只修一条路径）

跑法（不需重启任何服务，纯进程内）：
  NACOS_SERVER_ADDRESS=127.0.0.1:18848 DATA_ID=index_graph_config_py GROUP=DEFAULT_GROUP \
  platform/r12/venvs/graph/bin/python platform/r12/graph/test_summary_store_down.py
"""
import os
import sys

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

import graph_summary as gs  # noqa: E402


def run_case(mode):
    # 指向必然不可达的端口，模拟"ES 索引服务重启/挂掉"
    old = gs.ES_PORT
    gs.ES_PORT = 1
    try:
        resp = gs.query_community({"space_name": "kb_9", "query": "智造贷的加点规则",
                                   "mode": mode, "top_k": 5, "model_info": {}})
    finally:
        gs.ES_PORT = old
    code = getattr(resp, "code", None)
    msg = getattr(resp, "msg", "") or ""
    data = getattr(resp, "data", None) or {}
    err = (data or {}).get("error") if isinstance(data, dict) else None
    ok = (code == 500 and err == "summary_store_unavailable"
          and ("失败" in msg or "不可用" in msg))
    return {"mode": mode, "code": code, "msg": msg, "error": err, "ok": ok}


def main():
    results = [run_case("global"), run_case("local")]
    for r in results:
        print(f"  [{'PASS' if r['ok'] else 'FAIL'}] mode={r['mode']} code={r['code']} "
              f"error={r['error']} msg={r['msg'][:40]}")
    all_ok = all(r["ok"] for r in results)
    print(f"\n[结论] {'PASS' if all_ok else 'FAIL'}：摘要存储不可用时 global/local 均返回 500 且带错误码"
          if all_ok else
          f"\n[结论] FAIL：有路径仍把故障伪装成拒答 -> {[r for r in results if not r['ok']]}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
