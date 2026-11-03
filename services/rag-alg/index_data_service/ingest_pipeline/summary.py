"""表格总结通道（D-03）：补上投影缺的 `table_summary_<kb>`。

为什么需要（代码证据）
------------------
检索在 `enabled_summary=True` 时把 `table_summary_<kb>` 加进召回（`retrieval_service.py:54`，
主路径 `:397` 写死 True），命中后取 `doc.metadata["pk"]`，到 `table_chunks_<kb>` 里按
`table_summary_id in [...]` 拉明细（`multiple_retrieval.py:164`）。

因此链路要求：
  · 表格块必须有 `table_summary_id`（Milvus `_table_chunks_*` 确实有这个字段）；
  · 总结文档的 `pk` 必须等于该值（`_table_summary_*` 有 `table_id`/`text_chunk_id`，没有 summary_id）。

稳定 id 的取法（与 legacy 对齐的意图）
--------------------------------
legacy 的 `create_table_pk` 明确"绝不能用正文哈希"，因为总结文本是 LLM 生成的、每次不同。
这里同样用 `index_name|file_id|table_id` 做种子，保证同一张表每次得到同一个 id。

两种总结器
--------
- `llm_summarizer(...)`：调 OpenAI 兼容端点，要求保留数字与单位、≤120 字；
- `extractive_summarizer`：不调模型，取表头 + 前几行拼一句（离线/单测用），**明确标注来源**，
  避免把抽取式摘要当成 LLM 摘要。
"""

import hashlib
import json
import urllib.request


def table_summary_id(index_name, file_id, table_id):
    """总结文档主键（INT64）；写到表格块上时为它的十进制字符串。

    同表稳定、跨次解析不变：种子只用 index/file_id/table_id。
    """
    seed = f"v2sum|{index_name}|{file_id}|{table_id}"
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:15], 16)


def extractive_summarizer(text, table_id=None, meta=None):
    """不调模型：取前两行 + 行列数提示。用于离线与单测，输出带 `[extractive]` 标记。"""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    head = "；".join(lines[:2])[:160]
    return f"[extractive] 表格 {table_id or ''}：{head}"


def llm_summarizer(url="http://127.0.0.1:18092/v1/chat/completions",
                   model="qwen2.5-7b-instruct", timeout=120, api_key="sk-local"):
    """返回一个 summarizer(text, table_id, meta) -> str。失败时退回抽取式并标注。"""
    def _call(text, table_id=None, meta=None):
        prompt = ("用一句中文概括这张表格的内容与关键指标，必须保留表中的数字与单位，"
                  "不要编造表中没有的数值，不超过120字。\n\n表格内容：\n" + (text or "")[:3000])
        body = json.dumps({"model": model, "temperature": 0,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            out = (data["choices"][0]["message"]["content"] or "").strip()
            return out[:400] if out else extractive_summarizer(text, table_id)
        except Exception:  # noqa: BLE001 - 摘要失败不得阻断索引
            return extractive_summarizer(text, table_id)

    return _call


def build_summary_payloads(table_chunks, *, index_name, summarizer):
    """为每个表格块生成一条总结载荷，并把 `table_summary_id` 回填到表格块上。

    返回 (summary_payloads, updated_table_chunks)。
    """
    summaries, updated = [], []
    for chunk in table_chunks:
        meta = dict(chunk["metadata"])
        table_id = meta.get("table_id") or f"seq{meta.get('chunk_index')}"
        sid = table_summary_id(index_name, meta.get("file_id"), table_id)
        text = summarizer(chunk["page_content"], table_id, meta)
        # 生产 schema：`_table_chunks_*` 的 table_summary_id 是 VARCHAR，`_table_summary_*` 的 pk 是 INT64。
        # 反了会被 Milvus 拒绝（实测 "comparisons between VarChar and Int64 are not supported"）。
        meta["table_summary_id"] = str(sid)
        new_chunk = dict(chunk, metadata=meta)
        updated.append(new_chunk)

        summaries.append({
            "index": f"table_summary_{index_name}",
            "page_content": text,
            "pk": sid,
            "metadata": {
                "pk": sid,
                "type": "table_summary",
                "table_id": table_id,
                "table_name": meta.get("table_name", ""),
                "file_id": meta.get("file_id"),
                "source": meta.get("source"),
                "knowledge_base_name": index_name,
                "chunk_index": meta.get("chunk_index"),
                "parse_artifact_id": meta.get("parse_artifact_id"),
                "content_uid": meta.get("content_uid"),
                "channel": "table_summary",
            },
        })
    return summaries, updated
