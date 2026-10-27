#!/usr/bin/env python3
"""只在本地进程里跑 graph_summary.query_community（不重启服务、不写任何库），用于改法迭代。

用法：platform/r12/venvs/graph/bin/python platform/r12/graph/global_dev.py "问题"
"""
import json
import os
import sys
import time

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("NAMESPACE", "")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

import graph_summary as gs  # noqa: E402
import utils as _utils  # noqa: E402

# 独立进程里 nacos 合并配置不完整（缺 llm_server），补一个与运行态一致的桩；
# 其余属性（Nebula 会话池等）必须仍然代理到真实对象，否则 community_triples 读不到图。
_LLM = {"host": "127.0.0.1", "port": 18092,
        "api_name": "v1/chat/completions", "model": "qwen2.5-7b-instruct"}
_ORIG = _utils.return_nacos_model


class _Wrap:
    def __init__(self, real):
        self._real = real

    def get_config(self):
        cfg = dict(self._real.get_config() or {})
        cfg.setdefault("llm_server", _LLM)
        return cfg

    def __getattr__(self, k):
        return getattr(self._real, k)


_utils.return_nacos_model = lambda: _Wrap(_ORIG())

q = sys.argv[1]
t0 = time.time()
resp = gs.query_community({
    "space_name": "kb_9", "query": q, "mode": "global", "top_k": 5,
    "model_info": {"model_id": "qwen2.5-7b-instruct",
                   "url": "http://127.0.0.1:18092/v1/chat/completions", "key": "sk-r12-local"},
})
d = resp.data if isinstance(resp.data, dict) else {}
print(f"# code={resp.code} msg={resp.msg} cost={time.time()-t0:.1f}s")
print("answer:\n" + (d.get("answer") or ""))
print("\n# map_hit=", d.get("map_hit"), "map_used=", d.get("map_used"))
for c in d.get("communities") or []:
    print(f"  {c['community_id']} L{c.get('level')} members={len(c.get('members') or [])} "
          f"triples={len(c.get('triples') or [])} sources={c.get('sources')}")
    if c.get("facts"):
        print("   facts:", len(c["facts"]), "|", " ; ".join(c["facts"][:6])[:400])
