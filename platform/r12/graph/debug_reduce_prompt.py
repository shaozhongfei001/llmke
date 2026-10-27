#!/usr/bin/env python3
"""只读：重建 global reduce 的提示词并打印关键信息，用于判断"答案编造"是上下文缺失还是模型问题。

用法：
  platform/r12/venvs/graph/bin/python platform/r12/graph/debug_reduce_prompt.py "问题" [--call]
"""
import os
import sys

SVC = "/home/szf/data/dev/llmke-r12/services/rag-alg/index_data_service/index_graph_service"
sys.path.insert(0, SVC)
os.environ.setdefault("PYTHONPATH", SVC)
os.environ.setdefault("NACOS_SERVER_ADDRESS", "127.0.0.1:18848")
os.environ.setdefault("NAMESPACE", "")
os.environ.setdefault("DATA_ID", "index_graph_config_py")
os.environ.setdefault("GROUP", "DEFAULT_GROUP")

import graph_summary as gs  # noqa: E402

question = sys.argv[1] if len(sys.argv) > 1 else "测试"
kb = "kb_9"
summaries = gs._load_summaries(kb, with_triples=True)
lines = []
for s in summaries:
    block = [f"[{s['community_id']}] (level={s.get('level')})",
             f"成员实体: {', '.join(s.get('members') or [])}",
             f"摘要: {s['summary']}"]
    tr = s.get("triples") or []
    if tr:
        block.append("社区内事实:\n" + "\n".join(f"- {a} -{r}-> {b}" for a, r, b in tr[:80]))
    lines.append("\n".join(block))
prompt = gs.REDUCE_PROMPT.format(question=question, summaries="\n\n".join(lines))
print(f"# communities={len(summaries)} prompt_chars={len(prompt)}")
print("# contains AAA级加点幅度:", "AAA级加点幅度" in prompt)
print("# contains AA级加点幅度:", "AA级加点幅度" in prompt)
for s in summaries:
    print(f"  {s['community_id']} L{s.get('level')} members={len(s.get('members') or [])} triples={len(s.get('triples') or [])}")

if "--call" in sys.argv:
    from utils import return_nacos_model
    model_info = {"model_id": "qwen2.5-7b-instruct",
                  "url": "http://127.0.0.1:18092/v1/chat/completions", "key": "sk-r12-local"}
    answer = gs.requests_llm(prompt, model_info, return_nacos_model().get_config(), prompt_flag=True)
    print("\n===== ANSWER =====")
    print(answer)
