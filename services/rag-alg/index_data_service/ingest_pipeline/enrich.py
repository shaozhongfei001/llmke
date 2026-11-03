"""把投影块补齐成**能直接进生产集合**的元数据面（B1 剩余）。

依据（实测，非推测）
------------------
生产 `_kb_9` 共 33 字段，逐行统计 270 行后：
- 13 个字段 0/270（folder_id、title_path、labels、pic_url_list、text_parent_id_list、
  table_name、order_num、revise_date、image_path、att_id、main_id、pic_offset_list、
  pic_children_id_list）→ 数据集里本来就空，**不是缺口**，这里显式写空值保证类型对齐；
- 10 个字段 270/270：title、position、page_number、knowledge_base_name、file_path、
  file_size、page_size、parent_file_name、create_time、update_time → **必须补**。

同文件对照（file_id=333，docx）：生产里 position=`[[], []]`、page_number=`[0, 0]`、
page_size=`[[], []]`，即 Office 文件本来就只有占位值。所以投影对版面字段写同样的占位形状，
并**记入 `layout: unavailable`**——占位是兼容，不是"有版面信息"。

形状约定（与既有消费者一致）
--------------------------
- offset：`[[start, end], ...]`（旧链路是 list of pairs，不是 "a-b" 字符串）；
- page_number：`[int, ...]`；page_size：`[[w, h], ...]`；position：`[[[x, y], ...], ...]`；
- type：`text` / `table`。

刻意不做
--------
不臆造版面坐标：拿不到就写空列表 + 标记 unavailable，避免下游把占位当真实坐标做高亮。
"""

import os
import time

# 生产集合里恒空的字段（实测 0/270），显式写空值是为了类型/对齐，不是丢失
EMPTY_BY_DESIGN = ("folder_id", "title_path", "labels", "pic_url_list", "pic_offset_list",
                   "text_parent_id_list", "table_name", "order_num", "revise_date",
                   "image_path", "att_id", "main_id", "pic_children_id_list")

# 需要真实来源的字段（实测 270/270）
NEEDS_SOURCE = ("title", "parent_file_name", "knowledge_base_name", "file_path", "file_size",
                "create_time", "update_time", "offset", "page_number", "page_size", "position")


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def build_payload(chunk, *, index_name, file_id, file_name=None, file_path=None,
                  file_size=None, now=None):
    """返回 (payload, fill_report)。

    payload 的 `metadata` 覆盖生产集合的 33 个字段（缺的直接给空值），
    `fill_report` 说明每个字段是 filled / placeholder / empty_by_design。
    """
    name = file_name or (os.path.basename(file_path) if file_path else "")
    stamp = now or _now()
    loc = chunk.get("locator") or {}
    channel = chunk.get("channel", "text")

    if channel == "text" and "start_offset" in loc:
        offset = [[int(loc["start_offset"]), int(loc["end_offset"])]]
    else:
        offset = []

    meta = {
        # —— 有真实来源 ——
        "title": name,
        "parent_file_name": name,
        "knowledge_base_name": index_name,
        "file_path": file_path or "",
        "file_size": str(file_size) if file_size is not None else "",
        "create_time": stamp,
        "update_time": stamp,
        "file_id": str(file_id),
        "chunk_index": int(chunk["seq"]),
        "type": channel,
        "offset": offset,
        # 生产集合用这对字段定位"这条块属于哪份文档的哪个块"
        "chunk_doc_id": str(chunk["pk"]),
        "document_id": str(file_id),
        # —— 版面：拿不到就用旧链路的占位形状 ——
        "page_number": [0],
        "page_size": [[0, 0]],
        "position": [[]],
        # —— 恒空字段 ——
        "folder_id": "",
        "title_path": "",
        "labels": [],
        "pic_url_list": [],
        "pic_offset_list": [],
        "text_parent_id_list": [],
        "table_name": "",
        "order_num": "",
        "revise_date": "",
        "image_path": "",
        "att_id": [],
        "main_id": [],
        "pic_children_id_list": [],
        # —— V2 溯源（生产集合没有，但投影必须带，供审计/引用） ——
        "parse_artifact_id": chunk["parse_artifact_id"],
        "content_uid": chunk["content_uid"],
        "channel": channel,
    }
    if channel == "table":
        meta["table_id"] = loc.get("table_id")

    fill = {"filled": [k for k in NEEDS_SOURCE if meta.get(k) not in (None, "", [], [0], [[0, 0]], [[]])],
            "placeholder": [k for k in ("page_number", "page_size", "position")
                            if k not in () and meta[k] in ([0], [[0, 0]], [[]])],
            "empty_by_design": list(EMPTY_BY_DESIGN),
            "layout": "unavailable"}
    # offset 为空（表格块没有正文偏移）不算 filled，但也不该算缺口：表格有 table_id
    if not offset and channel == "table":
        fill["filled"] = [k for k in fill["filled"] if k != "offset"]
        fill["placeholder"] = fill["placeholder"] + ["offset(table)"]
    return meta, fill
