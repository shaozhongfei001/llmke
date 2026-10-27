#!/usr/bin/env python3
"""只读：把 kb 的社区及其 Nebula 三元组打印出来，用于核对 global 可归纳的事实边界。

用法：platform/r12/venvs/graph/bin/python platform/r12/graph/dump_community_triples.py kb_9
"""
import json
import os
import sys

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("NAMESPACE", "")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

from graph_community import community_triples  # noqa: E402

import requests  # noqa: E402

kb = sys.argv[1] if len(sys.argv) > 1 else "kb_9"
r = requests.post("http://127.0.0.1:19527/search_by_custom_param",
                  json={"index_name": [f"community_summary_{kb}"], "page_no": 1, "page_size": 50},
                  timeout=60)
rows = ((r.json() or {}).get("data") or {}).get("result_data") or []
print(f"# communities in ES: {len(rows)}")
out = []
for row in rows:
    md = (row.get("_source") or {}).get("metadata") or {}
    members = md.get("member_entities") or []
    triples, _ = community_triples(kb, members)
    uniq = sorted(set(tuple(t) for t in triples))
    print(f"\n### {md.get('community_id')} level={md.get('level')} members={len(members)} triples={len(uniq)}")
    for a, rel, b in uniq:
        print(f"  {a} -{rel}-> {b}")
    out.append({"community_id": md.get("community_id"), "level": md.get("level"),
                "members": members, "triples": [list(t) for t in uniq]})
print("\n" + json.dumps(out, ensure_ascii=False)[:200] + " ...")
