"""HippoRAG 适配层：native_id ↔ input_unit ↔ SourceRef 的映射（C1 的地基）。

为什么必须自己维护这张表
----------------------
`hipporag==2.0.0a4` 的 `HippoRAG.index(docs: List[str])` 只接受**纯文本**，
chunk 标识由 `chunk_embedding_store.insert_strings(docs)` 按内容生成（`get_all_id_to_rows()`）。
也就是说：

- 同一段正文若来自两个文件/两个块，会被算成**同一个 chunk_key**；
- HippoRAG 侧拿不到 file_id / offset / 快照身份，天然无法回答"这条来自哪里"；
- 若把它的 id 当公共身份，删一份来源会把另一份的引用一起带走（正是任务书禁止的"因正文相同丢来源/权限"）。

所以公共身份留在平台：`input_unit_id`（确定性、不含 HippoRAG 内部 id），
`native_key` 只是**缓存键**，允许 1:N —— 一个 native_key 下挂多个 input_unit，每个都带自己的 SourceRef。

刻意不做
--------
- 不 import hipporag：本模块不依赖 torch/vllm，可在无 GPU 环境跑；真正的引擎调用由 worker 负责。
- 不把相似边/无向投影写成业务断言：这里只做身份与来源映射。
"""

import hashlib
import json
import re

SCHEMA = "llmke.graph-engine.mapping.v1"
_NATIVE_KEY_RE = re.compile(r"^chunk-[0-9a-f]{32}$")


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def native_key(text):
    """引擎侧 chunk 键，**实测**为 `chunk-<md5(正文)>`（hipporag 2.0.0a4）。

    核对方式：`hp.chunk_embedding_store.get_all_id_to_rows()` 的键与 md5(正文) 逐条对齐。
    它只用于**把平台侧单元对到引擎侧 chunk**，绝不对外暴露、也不用作事实身份：
    同文不同源会得到同一个键，靠 SourceMap 的 1:N 保住来源。
    """
    return "chunk-" + hashlib.md5(text.encode("utf-8")).hexdigest()


def input_unit_id(parse_artifact_id, seq, channel="text"):
    """平台侧稳定标识：同一快照 + 同一通道 + 同一块号 → 同一个 id，换引擎不变。

    必须带 channel：投影的正文块与表格块各自从 0 编号，只有 (artifact, seq) 会撞车
    （实测两个不同表的 seq=0 撞成同一个单元，直接抛"同一 id 不同正文"）。
    """
    return _sha256(f"{parse_artifact_id}:{channel}:{seq}")


class InputUnit:
    """一个待送入图引擎的输入单元，携带它自己的来源。"""

    __slots__ = ("input_unit_id", "native_key", "text", "content_uid", "parse_artifact_id",
                 "seq", "source_ref", "channel")

    def __init__(self, text, *, content_uid, parse_artifact_id, seq, source_ref,
                 channel="text"):
        self.text = text
        self.content_uid = content_uid
        self.parse_artifact_id = parse_artifact_id
        self.seq = int(seq)
        self.source_ref = dict(source_ref)
        self.channel = channel
        self.input_unit_id = input_unit_id(parse_artifact_id, seq, channel)
        self.native_key = native_key(text)

    def as_dict(self):
        return {"input_unit_id": self.input_unit_id, "native_key": self.native_key,
                "content_uid": self.content_uid, "parse_artifact_id": self.parse_artifact_id,
                "seq": self.seq, "channel": self.channel, "source_ref": self.source_ref}


class SourceMap:
    """native_key -> [InputUnit] 的多对一映射；一个引擎 chunk 可以有多个来源。"""

    def __init__(self):
        self._by_native = {}
        self._by_unit = {}

    def add(self, unit):
        # 同一快照同一 seq 重复登记是幂等的；内容变了就必须换 artifact_id，不允许静默覆盖
        if unit.input_unit_id in self._by_unit:
            existing = self._by_unit[unit.input_unit_id]
            if existing.native_key != unit.native_key:
                raise ValueError(f"同一 input_unit_id 出现不同正文: {unit.input_unit_id}")
            return existing
        self._by_unit[unit.input_unit_id] = unit
        self._by_native.setdefault(unit.native_key, []).append(unit)
        return unit

    def extend(self, units):
        for unit in units:
            self.add(unit)
        return self

    def units_for(self, key):
        return list(self._by_native.get(key, []))

    def sources_for(self, key):
        """引擎侧 chunk_key → 全部 SourceRef（去重但保留多来源）。"""
        out, seen = [], set()
        for unit in self._by_native.get(key, []):
            marker = json.dumps(unit.source_ref, sort_keys=True, ensure_ascii=False)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(unit.source_ref)
        return out

    def stats(self):
        multi = {k: len(v) for k, v in self._by_native.items() if len(v) > 1}
        return {"units": len(self._by_unit), "engine_chunks": len(self._by_native),
                "shared_chunks": len(multi), "max_sources_per_chunk": max(multi.values(), default=1)}

    def to_json(self):
        return {"schema": SCHEMA,
                "units": [u.as_dict() for u in self._by_unit.values()],
                "chunks": {k: [u.input_unit_id for u in v] for k, v in self._by_native.items()}}

    @classmethod
    def from_json(cls, payload):
        if payload.get("schema") != SCHEMA:
            raise ValueError(f"映射表 schema 不匹配: {payload.get('schema')!r}")
        sm = cls()
        for rec in payload["units"]:
            unit = InputUnit(rec.get("text") or "",  # 正文不入库时为空，native_key 以登记值为准
                             content_uid=rec["content_uid"],
                             parse_artifact_id=rec["parse_artifact_id"], seq=rec["seq"],
                             source_ref=rec["source_ref"], channel=rec.get("channel", "text"))
            if unit.input_unit_id != rec["input_unit_id"]:
                raise ValueError("input_unit_id 不自洽，拒绝加载（可能被篡改或算法变更）")
            recorded = rec.get("native_key")
            if recorded:
                # 形如 chunk-<md5>；正文不入库时靠这个字段还原，必须校验形态
                if not _NATIVE_KEY_RE.match(str(recorded)):
                    raise ValueError(f"native_key 形态非法: {recorded!r}")
                unit.native_key = recorded
            sm.add(unit)
        return sm


def units_from_chunks(chunks, *, file_id=None):
    """把 `ingest_pipeline` 产出的 chunk 载荷转成输入单元（保持一块一来源）。"""
    units = []
    for chunk in chunks:
        meta = chunk["metadata"]
        units.append(InputUnit(
            chunk["page_content"],
            content_uid=meta["content_uid"],
            parse_artifact_id=meta["parse_artifact_id"],
            seq=meta["chunk_index"],
            channel=meta.get("channel", "text"),
            source_ref={"file_id": str(meta.get("file_id", file_id or "")),
                        "source": meta.get("source", ""),
                        "offset": meta.get("offset") or [],
                        "table_id": meta.get("table_id"),
                        "parse_artifact_id": meta["parse_artifact_id"]}))
    return units
