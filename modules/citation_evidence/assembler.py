"""引用证据组装器：把检索片段组装成契约允许的 DocumentEvidence。

约束来源（冻结契约，不可改）：
- contracts/evidence/llmke-citation-evidence.yaml: offset_unit=unicode_codepoint
- contracts/schema/llmke-core.json#/$defs/{Evidence,DocumentEvidence,SourceRef,Offset}

设计要点：
1. **禁止伪造 offset**：不信任调用方给的 text_hash，一律用 text[start:end] 重算并比对；
2. 越界即失败（0 <= start < end <= len(text)，Python str 下标即码点，天然满足码点语义）；
3. 输出对象严格裁剪到 schema 允许的字段（additionalProperties=false），不夹带内部字段；
4. 所有失败走 EvidenceError，带机器可读 code，便于上层 fail-closed。
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

CORE_SCHEMA = "contracts/schema/llmke-core.json"
UNIT = "unicode_codepoint"


class EvidenceError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _need_str(value: Any, name: str, maxlen: int = 256) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError("FIELD_MISSING", f"{name} 必须是非空字符串")
    if len(value) > maxlen:
        raise EvidenceError("FIELD_TOO_LONG", f"{name} 超过 {maxlen}")
    return value


def _hex64(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise EvidenceError("HASH_FORMAT", f"{name} 必须是 64 位小写十六进制")
    return value


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_document_evidence(document_text: str, source: dict, evidence_id: str) -> dict:
    """组装 DocumentEvidence；任何不可信输入一律抛错，不返回"部分正确"的对象。"""
    if not isinstance(document_text, str):
        raise EvidenceError("ILLEGAL_INPUT", "document_text 必须是 str")
    if not isinstance(source, dict):
        raise EvidenceError("ILLEGAL_INPUT", "source 必须是 dict")
    _need_str(evidence_id, "evidence_id")

    offset = source.get("offset")
    if not isinstance(offset, dict):
        raise EvidenceError("FIELD_MISSING", "source.offset 缺失")

    start, end = offset.get("start"), offset.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or isinstance(start, bool) or isinstance(end, bool):
        raise EvidenceError("OFFSET_TYPE", "start/end 必须是整数")
    if start < 0 or end < 1 or start >= end:
        raise EvidenceError("OFFSET_RANGE", f"要求 0 <= start < end，实际 {start}..{end}")
    if end > len(document_text):
        raise EvidenceError("OFFSET_OUT_OF_BOUNDS", f"end={end} 超出文本长度 {len(document_text)}")

    if offset.get("unit") != UNIT:
        raise EvidenceError("OFFSET_UNIT", f"unit 必须是 {UNIT}")

    _need_str(offset.get("parser_version"), "offset.parser_version")

    slice_text = document_text[start:end]
    actual = text_hash(slice_text)
    declared = offset.get("text_hash")
    _hex64(declared, "offset.text_hash")
    if actual != declared:
        # 这是"伪造 offset"的核心防线：声称的区间与声称的哈希对不上
        raise EvidenceError("OFFSET_TEXT_HASH_MISMATCH", f"实际 {actual[:12]}… 与声明不一致")

    _hex64(source.get("content_hash"), "source.content_hash")

    # 严格裁剪，避免把内部字段写进对外契约
    return {
        "evidence_id": evidence_id,
        "type": "document_text",
        "source_ref": {
            "kb_id": _need_str(source.get("kb_id"), "source.kb_id"),
            "file_id": _need_str(source.get("file_id"), "source.file_id"),
            "document_version": _need_str(source.get("document_version"), "source.document_version"),
            "chunk_id": _need_str(source.get("chunk_id"), "source.chunk_id"),
            "content_hash": source["content_hash"],
            "offset": {
                "start": start,
                "end": end,
                "unit": UNIT,
                "text_hash": actual,
                "parser_version": offset["parser_version"],
            },
        },
    }


def _document_key(ev: dict) -> tuple:
    """同一份"文档版本"的身份：kb + file + document_version。chunk_id 刻意排除。"""
    r = ev["source_ref"]
    return (r["kb_id"], r["file_id"], r["document_version"])


def check_evidence_set(evidence: list[dict]) -> None:
    """集合级完整性校验（单条装配看不到的问题）。

    三类真实缺陷：
    1. **重复 evidence_id**：同一 id 指向两段不同文本时，上层按 id 去重会静默丢证据，
       按 id 索引又会取到错误片段。→ DUPLICATE_EVIDENCE_ID
    2. **parser_version 混用**：offset 是"码点下标"，其含义由解析器版本决定。
       同一 document_version 下出现两个解析器版本，等价于"同一版本文档有两套坐标系"，
       区间之间不再可比：重叠判定会失真，页码/高亮回填会错位。
       版本语义被破坏，必须由上游升 document_version，而不是在这里折中。
       → PARSER_VERSION_MIXED
    3. **区间重叠**：
       - 同一 chunk 内两段重叠 → 证据重复计数（支撑率虚高）→ SAME_CHUNK_OVERLAP
       - 不同 chunk 但区间重叠 → 切分器产出重叠块，同一段原文被两个 chunk 同时认领，
         去重后仍会互相"佐证"，是更隐蔽的虚高来源 → CROSS_CHUNK_OVERLAP
    区间为左闭右开，因此 `end == next.start` 相邻不算重叠。
    """
    seen: dict[str, int] = {}
    for i, ev in enumerate(evidence):
        eid = ev["evidence_id"]
        if eid in seen:
            raise EvidenceError(
                "DUPLICATE_EVIDENCE_ID",
                f"{eid} 出现在第 {seen[eid]} 与第 {i} 条")
        seen[eid] = i

    # parser_version 一致性：同一文档版本只能有一套 offset 坐标系
    versions: dict[tuple, tuple] = {}
    for ev in evidence:
        key = _document_key(ev)
        pv = ev["source_ref"]["offset"]["parser_version"]
        prev = versions.get(key)
        if prev is None:
            versions[key] = (pv, ev["evidence_id"])
        elif prev[0] != pv:
            raise EvidenceError(
                "PARSER_VERSION_MIXED",
                f"{key[1]}@{key[2]}: {prev[1]} 来自 {prev[0]}，"
                f"{ev['evidence_id']} 来自 {pv}；offset 不可比，须由上游升 document_version")

    groups: dict[tuple, list[tuple]] = {}
    for ev in evidence:
        off = ev["source_ref"]["offset"]
        groups.setdefault(_document_key(ev), []).append(
            (off["start"], off["end"], ev["source_ref"]["chunk_id"], ev["evidence_id"]))

    for key, spans in groups.items():
        spans.sort()
        cur_start, cur_end, cur_chunk, cur_eid = spans[0]
        for start, end, chunk, eid in spans[1:]:
            if start < cur_end:
                code = ("SAME_CHUNK_OVERLAP" if chunk == cur_chunk
                        else "CROSS_CHUNK_OVERLAP")
                raise EvidenceError(
                    code,
                    f"{key[1]}@{key[2]}: {cur_eid}[{cur_start},{cur_end}) 与 "
                    f"{eid}[{start},{end}) 重叠（chunk {cur_chunk} / {chunk}）")
            # 保留覆盖最远的区间，避免"短区间被长区间吞掉"后漏检
            if end > cur_end:
                cur_start, cur_end, cur_chunk, cur_eid = start, end, chunk, eid


def assemble_many(items: list[dict], repo_root: Path | str | None = None,
                  validate: bool = False) -> list[dict]:
    """批量装配 + 集合级校验。空集合视为失败（fail-closed，不返回"零证据的成功"）。"""
    if not isinstance(items, list):
        raise EvidenceError("ILLEGAL_INPUT", "items 必须是数组")
    if not items:
        raise EvidenceError("EMPTY_EVIDENCE_SET", "证据集合为空")

    built = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise EvidenceError("ILLEGAL_INPUT", f"第 {i} 项必须是对象")
        try:
            built.append(build_document_evidence(
                item["document_text"], item["source"], item["evidence_id"]))
        except KeyError as e:
            raise EvidenceError("FIELD_MISSING", f"第 {i} 项缺少 {e}") from e

    check_evidence_set(built)
    if validate:
        for ev in built:
            validate_evidence(ev, repo_root if repo_root is not None else Path("."))
    return built


def _load_core(repo_root: Path) -> dict:
    p = Path(repo_root) / CORE_SCHEMA
    if not p.is_file():
        raise EvidenceError("CONTRACT_MISSING", str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def validate_evidence(evidence: dict, repo_root: Path | str) -> None:
    """用冻结契约本体校验；失败抛 EvidenceError，便于 fail-closed 集成。

    实现说明（2026-10-21）：原先用已废弃的 `jsonschema.RefResolver`，
    在 jsonschema ≥4.18 会产生 DeprecationWarning 且未来会移除。
    改为 `referencing` 显式注册契约文档，并在 `$ref` 上带基 URI 解析——
    语义等价，且不再依赖已弃用 API。
    """
    from jsonschema import Draft202012Validator
    from referencing import Registry
    from referencing.jsonschema import DRAFT202012

    core = _load_core(Path(repo_root))

    # 契约内部用的是「文件名相对引用」（如 llmke-core.json#/$defs/SourceRef）。
    # 这些引用全部指向同一份文档，因此归一化为文档内锚点，再用单一基 URI 解析。
    def _inline(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("llmke-core.json#"):
                node["$ref"] = ref[len("llmke-core.json"):]
            for v in node.values():
                _inline(v)
        elif isinstance(node, list):
            for v in node:
                _inline(v)
    _inline(core)

    base_uri = "urn:llmke:core"
    registry = Registry().with_resources(
        [(base_uri, DRAFT202012.create_resource(core))]
    )
    v = Draft202012Validator({"$ref": f"{base_uri}#/$defs/DocumentEvidence"}, registry=registry)
    errs = sorted(v.iter_errors(evidence), key=lambda e: list(e.path))
    if errs:
        first = errs[0]
        raise EvidenceError("CONTRACT_VIOLATION", f"{list(first.path)}: {first.message}")


class SupportGate:
    """按契约 `unsupported_policy: [block, annotate]` 过滤声明。

    规则（来自 contracts/evidence/llmke-citation-evidence.yaml）：
    - 有证据的声明：放行，附带证据 id 列表；
    - 无证据的声明：**默认 block**（blocked claims never emitted），不得静默丢弃；
    - 调用方显式要求 annotate 时，才允许作为"未支持标注"返回，并保留原因。
    """

    def __init__(self, mode: str = "block"):
        if mode not in ("block", "annotate"):
            raise EvidenceError("ILLEGAL_MODE", "mode 只能是 block 或 annotate")
        self.mode = mode

    def partition(self, claims: list[dict]) -> dict:
        supported, blocked = [], []
        for c in claims:
            cid = c.get("claim_id")
            if not isinstance(cid, str) or not cid:
                raise EvidenceError("CLAIM_ID", "每个 claim 必须有非空 claim_id")
            ev = c.get("evidence_ids") or []
            if not isinstance(ev, list) or not all(isinstance(x, str) and x for x in ev):
                raise EvidenceError("EVIDENCE_IDS", f"{cid}: evidence_ids 必须是非空字符串数组")
            if ev:
                supported.append({"claim_id": cid, "evidence_ids": ev, "text": c.get("text", "")})
            else:
                blocked.append({"claim_id": cid, "reason": "NO_APPROVED_EVIDENCE",
                                "text": c.get("text", "")})

        out = {"mode": self.mode, "supported": supported, "blocked": blocked,
               "emit": supported, "annotations": []}
        if self.mode == "annotate":
            # annotate 只允许"标注为未支持"，不得把无证据声明当成已支持发出
            out["annotations"] = [{"claim_id": b["claim_id"], "label": "unsupported",
                                   "reason": b["reason"]} for b in blocked]
        if self.mode == "block":
            # 硬约束：blocked 的声明绝不能出现在 emit 里
            assert not any(b["claim_id"] in {s["claim_id"] for s in out["emit"]} for b in blocked)
        return out


def _support_policy(repo_root: Path | str) -> dict:
    """从契约读审计阈值，避免把 0.95 / 30 之类数字硬编码进代码。"""
    import yaml  # 框架已依赖
    p = Path(repo_root) / "contracts/evidence/llmke-citation-evidence.yaml"
    if not p.is_file():
        raise EvidenceError("CONTRACT_MISSING", str(p))
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    # 契约顶层是 evidence:，support_audit 在其下；同时兼容未来提到顶层
    policy = ((doc.get("evidence") or {}).get("support_audit")
              or doc.get("support_audit") or {})
    try:
        return {"minimum_claims": int(policy["minimum_claims"]),
                "supported_ratio_min": float(policy["supported_ratio_min"])}
    except (KeyError, TypeError, ValueError) as e:
        raise EvidenceError("CONTRACT_MISSING", "support_audit 字段不全") from e


def audit_support(claims: list[dict], repo_root: Path | str) -> dict:
    """支持率审计：契约要求 minimum_claims 与 supported_ratio_min。

    返回可判定的结论；**不生成**任何批准记录，仅给出是否达到契约阈值。
    """
    policy = _support_policy(repo_root)
    total = len(claims)
    supported = sum(1 for c in claims if (c.get("evidence_ids") or []))
    ratio = (supported / total) if total else 0.0
    enough_samples = total >= policy["minimum_claims"]
    ratio_ok = ratio >= policy["supported_ratio_min"]
    return {
        "total_claims": total,
        "supported": supported,
        "ratio": round(ratio, 4),
        "minimum_claims": policy["minimum_claims"],
        "supported_ratio_min": policy["supported_ratio_min"],
        "samples_sufficient": enough_samples,
        "ratio_ok": ratio_ok,
        "verdict": "PASS" if (enough_samples and ratio_ok) else "FAIL",
        "reason": ("" if enough_samples and ratio_ok else
                   ("CLAIMS_BELOW_MINIMUM" if not enough_samples else "RATIO_BELOW_MINIMUM")),
    }
