# 检索层 metadata 白名单丢审计字段（改造前基线）

采集时刻：2026-10-27T11:20+08:00
代码位置：`services/rag-alg/alg_retrieval_service/app/retrieval_fun_tool.py:455-495`（逐字段 `.get()` 重建 metadata 的硬编码白名单）

## 复现命令

```bash
curl -s -X POST 127.0.0.1:19995/retrieval_documents \
  -H 'Content-Type: application/json' \
  -d '{"query":"智造贷的授信额度","knowledge_base_name":["kb_5","kb_9"],
       "enabled_graph":true,"enabled_rerank":false,"enabled_faq":false,"top_k":5}' \
| python3 -c "
import json,sys
d=json.load(sys.stdin); r=(d.get('data') or {}).get('documents_list') or []
print('code',d.get('code'),'docs',len(r))
for x in r[:5]:
    md=x.get('metadata') or {}
    print('-', str(md.get('title'))[:40],
          '| provenance_quality=', md.get('provenance_quality'),
          '| identity_stability=', md.get('identity_stability'),
          '| recovered_by=', md.get('recovered_by'),
          '| search=', md.get('search'),
          '| search_type=', md.get('search_type'))
"
```

## 实测输出（改造前）

```
code 200 docs 2
- None | provenance_quality= None | identity_stability= None | recovered_by= None | search= None
- None | provenance_quality= None | identity_stability= None | recovered_by= None | search= None
```

返回文档的 metadata 键（白名单结果，节选）：
`chunk_index, chunk_type, file_id, file_path, id, image_path, labels, offset, page_number,
page_size, parent_file_name, pic_children_id_list, pic_offset_list, position, ...`

## 判读

- 被丢弃的**审计字段**：`provenance_quality`、`identity_stability`、`recovered_by`、
  `recovered_entities`、`recovered_es_id`、`recovered_chunk_ref`、`id_origin`。
- 被丢弃的**展示字段**：`title`、`search`（`search_type` 与 `source` 保留）。
- 危险点（B-graph 补充）：`search_type` 保留 → 检索结果"看起来有 graph 标记"，
  但**无法判断这条图块是 `chunk_pk_list` 精确命中还是按实体名兜底**；
  "外观足够、质量不可判"比"字段完全缺失"更容易产出假绿断言。
- 另：`order_num = str(create_uuid())`（`:491`）每次请求随机，不可当引用稳定性证据。

## 判定口径（改造前）

任何"检查 `provenance_quality` / `identity_stability` / `recovered_*` / `id_origin`"的断言，
若写在 19995 / 网关响应上 → **必红**，且红的原因是链路丢字段，不是实现缺失。
改造前请直连 19529（图服务）或 ES 取证；或在断言里把"`search_type` 含 graph 但无
`provenance_quality`"显式记为 `UNVERIFIED_WHITELIST`，**不得判 PASS**。

## 建议改法（已交 C-business）

1. 最小改动：白名单补 7 个审计键 + `title` + 保留 `search`；
2. 更稳：改为"排除大字段后透传"——黑名单 `{base64, boxes, table_html_content, page_content, position?, offset?}`，
   其余键 `setdefault` 合并，避免审计字段每次新增都要改检索层。
