# T-B1 落地证据：B01 方向语义补丁合入 V2（2026-11-03，评审会话接管执行）

- 补丁：`/home/szf/data/dev/delivery/review-42167f0/03_补充材料/B01-r12-0bac08a.patch`（0bac08a format-patch）
- 落地：`git apply` 成功（此前 `git apply --check` exit 0）
- 改动文件：
  - `services/rag-alg/index_data_service/index_graph_service/graph_types.py`（pair_key 有向、undirected_pair_key 降级、本体分流）
  - `tests/test_graph_direction_b01.py`（新增，140 行）

## 复跑输出（本机实测）

```
$ python3 -m pytest -p no:cacheprovider tests/test_graph_direction_b01.py -q
............................                                             [100%]
28 passed in 0.04s

$ cd services/rag-alg/index_data_service && PYTHONPATH=. \
  /home/szf/data/dev/hipporag-toolenv/bin/python -m pytest -p no:cacheprovider \
  ../../../tests/test_graph_api.py ../../../tests/test_graph_engine_capabilities.py \
  ../../../tests/test_retrieval_shim.py ../../../tests/test_graph_global.py -q
.............................................................            [100%]
61 passed in 0.58s
```

- 旧实现确认消失：`graph_types.py:454` 起 `pair_key` 仅对称谓词走 `tuple(sorted(...))`，其余有向；
  `PAIR_KEY_SCHEME = "b01-ontology-directed-v1"`。
- 未做（如实）：存量 `g_kb_9` 清库重写（T-B2 待批：需写入冻结+授权+nebula3 客户端）。
