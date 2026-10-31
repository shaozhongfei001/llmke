#!/usr/bin/env python
"""生成验收用的"投影载荷"（ingest 输出形状），让 Q 不再依赖手工前置文件。

为什么需要：验收脚本里有 6 项图检查都读 `/tmp/ingest-333.json`、`/tmp/ingest-329.json`。
换台机器、或 /tmp 被清掉，这些检查就整片 SKIP——"跳过"看起来无害，实际等于
验收范围悄悄缩水。所以缺文件时要能**自己造**，而不是等人预先准备好。

内容与真实投影对齐（34 字段元数据、正文/表格双通道），不是随便凑几段文本：
- 333：docx，2 段正文 + 1 个表格块（多指标对账口径）
- 329：xlsx，1 段正文（授信台账 markdown）+ 1 个表格块

不做的事：不解析真实文档、不连数据库。这里只保证"形状与字段与生产一致"，
用于验收的是图引擎/映射层，不是解析层。
"""

import argparse
import hashlib
import json
import os

SCHEMA = "llmke.projection-payload.v1"

DOCX_CHUNKS = [
    ("# DOCX with table", "text", "kb_9"),
    ("下表为多指标对账口径。", "text", "kb_9"),
    ("指标 | 数据源 | 口径 | 日均存款 | T-CORE-001 | 按业务日跨账户汇总/天数 "
     "| 用电量 | T-EXT-001 | 月度同比", "table", "table_chunks_kb_9"),
]

XLSX_CHUNKS = [
    ("## 授信台账 | | 客户名称 | 所属产业链 | 信用评级 | 授信额度(万元) | 已用额度(万元) "
     "| 五级分类 | 到期日 | | | --- | --- | --- | --- | --- | --- | --- | | "
     "| 华东精密制造有限公司 | 汽车零部件 | AA | 3000 | 1800 | 正常 | 2027-03-31 | | "
     "| 江南装备科技有限公司 | 装备制造 | AAA | 5000 | 3200 | 正常 | 2027-06-30 | | "
     "| 海川电子材料股份有限公司 | 电子信息 | A | 1200 | 600 | 正常 | 2027-01-31 |",
     "text", "kb_9"),
    ("客户名称 | 所属产业链 | 信用评级 | 授信额度(万元) | 已用额度(万元) | 五级分类 | 到期日 | "
     "华东精密制造有限公司 | 汽车零部件 | AA | 3000 | 1800 | 正常 | 2027-03-31 | "
     "江南装备科技有限公司 | 装备制造 | AAA | 5000 | 3200 | 正常 | 2027-06-30 | "
     "海川电子材料股份有限公司 | 电子信息 | A | 1200 | 600 | 正常 | 2027-01-31",
     "table", "table_chunks_kb_9"),
]

FILES = {
    "333": {"title": "docx-table.docx", "kind": "docx", "chunks": DOCX_CHUNKS,
            "size": "1.2 MB"},
    "329": {"title": "analysis-report.xlsx", "kind": "xlsx", "chunks": XLSX_CHUNKS,
            "size": "0.4 MB"},
}


def meta_base(file_id, spec, index, kind, channel):
    digest = hashlib.sha256(f"{file_id}:{index}:{channel}".encode()).hexdigest()
    return {
        "title": spec["title"],
        "parent_file_name": spec["title"],
        "knowledge_base_name": "kb_9",
        "file_path": f"r12-rag/kb_9/{spec['title']}",
        "file_size": spec["size"],
        "create_time": "2026-10-31 00:44:55",
        "update_time": "2026-10-31 00:44:55",
        "file_id": file_id,
        "chunk_index": index if channel == "text" else max(index - 1, 0),
        "type": kind,
        "offset": [[0, 17]],
        "chunk_doc_id": str(911535714083224286 + index),
        "document_id": file_id,
        "page_number": [0],
        "page_size": [[0, 0]],
        "position": [[]],
        "folder_id": "",
        "title_path": "",
        "labels": [],
        "pic_url_list": [],
        "pic_offset_list": [],
        "text_parent_id_list": [],
        "table_name": "" if channel == "text" else "sheet1",
        "order_num": "",
        "revise_date": "",
        "image_path": "",
        "att_id": [],
        "main_id": [],
        "pic_children_id_list": [],
        "parse_artifact_id": digest,
        "content_uid": digest,
        "channel": channel,
        "source": f"r12-rag/kb_9/{spec['title']}/V0/{spec['title']}",
        "parsed_text_ref": "parsed_text.md" if channel == "text" else "parsed_tables.md",
    }


def build_payload(file_id):
    spec = FILES[file_id]
    chunks, channels = [], {}
    for i, (text, kind, channel) in enumerate(spec["chunks"]):
        channels[channel] = channels.get(channel, 0) + 1
        chunks.append({"index": channel, "page_content": text,
                       "metadata": meta_base(file_id, spec, i, kind, channel),
                       "pk": hashlib.sha256(f"{file_id}:{i}".encode()).hexdigest()[:16]})
    counts = {channel: n for channel, n in channels.items()}
    return {"status": "OK", "mode": "projection", "schema": SCHEMA,
            "artifact_id": hashlib.sha256(file_id.encode()).hexdigest(),
            "artifact_quality": {"status": "OK", "score": 1.0},
            "counts": counts, "channels": channels, "chunks": chunks,
            "field_fill": {"required_given": 10, "constant_empty": 13,
                           "layout_unavailable": "position/page_size"}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/tmp")
    ap.add_argument("--files", nargs="+", default=sorted(FILES))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    written, skipped = [], []
    for file_id in args.files:
        if file_id not in FILES:
            raise SystemExit(f"未知 file_id: {file_id}（可用：{sorted(FILES)}）")
        path = os.path.join(args.out_dir, f"ingest-{file_id}.json")
        if os.path.isfile(path) and not args.force:
            skipped.append(path)
            continue
        payload = build_payload(file_id)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        written.append(path)

    print(json.dumps({"written": written, "skipped": skipped,
                      "chunks": {f: len(FILES[f]["chunks"]) for f in args.files}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
