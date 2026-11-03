"""doc2md 产物绑定：把"同一份解析产物"变成可校验的公共身份（D1）。

为什么需要这一层
--------------
`/v2/graph/build` 现在只收 `{file_id, text, locator}`（见 `api.py:38` 的 `BuildDoc`）。
也就是说：图索引与 RAG 各拿一份正文，谁也无法证明二者出自**同一次解析**。
正文相同但产物不同（换了解析器版本、改了表格抽取）时，两边会静默错配 —— 这正是 D1
要求"RAG 与图谱绑定同一 ParseArtifact（artifact_id + 内容哈希）"的原因。

本模块只做**纯函数校验与归一**：不读文件、不联网、不 import 引擎，可以在无 GPU 的
环境跑。接入 `api.py` / 建图流程是后续步骤（本模块刻意不碰）。

字段口径（以合同为准，不自造）
--------------------------
- `artifact_id`：`contracts/schema/llmke-document-pipeline-v2.json` 中 `ParseArtifact.artifact_id`
  与 `SourceRefV2.parse_artifact_id` 同源；本模块要求 64 位小写十六进制，因为下游
  `graph_engine_adapter.mapping.input_unit_id()` 直接把它拼进哈希，非定长/含分隔符的
  值会让不同 (artifact, seq, channel) 组合撞成同一个 id。
- `locator`：合同里 `Block.locator` 是结构化对象（`TextLocator`/`CellLocator`/`FigureLocator`），
  投影侧也可能给字符串（`"p1"`、`"table:r2"`）。两者都接受，但**都必须非空**：
  D7 要求可定位，缺 locator 的块在引用收口时无法回指原文。
- `file_id`：合同 `SourceRefV2.file_id`；缺省回落到 `document_id`，因为同一产物的块
  通常同属一份文件。
"""

import hashlib
import json
import re

# 聚合口径的版本标记。为什么要写进哈希：换个聚合规则（比如从"有序块"改成"去重块"）
# 时，hash 必须变，否则同一 artifact_id 下两种不同口径会算出同一个值，绑定就失效了。
CONTENT_SPEC = "llmke.artifact-binding.chunks/1"

_ARTIFACT_ID_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# chunk 自带的哈希字段名。合同里叫 `quote_hash`(TextLocator) / `cell_text_hash`(CellLocator)，
# 投影/调用方常见的别名是这些；多认几个名字是为了让"产物被改过"能被抓住，而不是漏检。
_CHUNK_HASH_KEYS = ("text_sha256", "content_hash", "hash", "sha256")

# 合同定义的三类定位器；dict 形式的 locator 必须带 `kind` 且落在闭集里，
# 否则我们无法判断它是"哪种可定位"，等于没有 locator。
_LOCATOR_KINDS = ("text_span", "table_cell", "figure_asset")


class ArtifactBindingError(ValueError):
    """绑定失败。继承 ValueError：调用方按"输入不合法"处理，而不是当程序缺陷。"""


def _sha256(text):
    # 与合同一致：按 unicode codepoint 取 UTF-8 字节再哈希（TextLocator.unit 的约定）。
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_hex64(value, field):
    """artifact_id / 自带哈希必须是 64 位小写十六进制。

    为什么 fail-closed：只要允许"不认识的形状"通过，`assert_same_artifact` 的两个字符串
    比较就可能永远不相等或永远相等，绑定检查退化成摆设。
    """
    if not isinstance(value, str) or not _HEX64_RE.match(value):
        raise ArtifactBindingError(f"{field} 必须是 64 位小写十六进制，实际为 {value!r}")
    return value


def _locator_key(locator):
    """把 locator 归一成可哈希的稳定键（**不改变输出的 locator 本身**）。

    dict 形式按 `sort_keys` 序列化：合同对象的键序不承载语义，若按插入序参与哈希，
    同一份产物换个序列化实现就会算出不同 content_hash，误报"产物被改"。
    """
    if isinstance(locator, str):
        return locator
    return json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _check_locator(locator, index):
    if locator is None:
        # 缺 locator 直接拒绝（D7）：没有定位信息的块只能被"召回"，不能被"引用"。
        raise ArtifactBindingError(f"chunk[{index}] 缺少 locator（D7 要求可定位）")
    if isinstance(locator, str):
        if not locator.strip():
            raise ArtifactBindingError(f"chunk[{index}] 的 locator 为空字符串")
        return locator
    if isinstance(locator, dict):
        if not locator:
            raise ArtifactBindingError(f"chunk[{index}] 的 locator 是空对象")
        kind = locator.get("kind")
        if kind not in _LOCATOR_KINDS:
            # 只认合同闭集：自造 kind 会让下游 locator 渲染/回指无解释分支。
            raise ArtifactBindingError(
                f"chunk[{index}] 的 locator.kind={kind!r} 不在合同闭集 {_LOCATOR_KINDS}")
        return locator
    raise ArtifactBindingError(
        f"chunk[{index}] 的 locator 类型不支持：{type(locator).__name__}")


def bind_artifact(artifact):
    """校验一个 ParseArtifact 投影并输出绑定后的 docs 列表。

    输入形如::

        {"artifact_id": "<64 hex>", "document_id": "...", "chunks": [
            {"text": "...", "locator": "p1", "file_id": "..."}, ...]}

    输出::

        {"artifact_id", "document_id", "content_hash",
         "docs": [{"file_id", "text", "locator", "artifact_id"}, ...]}

    docs 顺序与输入一致（顺序是内容的一部分：换序即换产物）。
    """
    if not isinstance(artifact, dict):
        raise ArtifactBindingError(f"artifact 必须是 dict，实际为 {type(artifact).__name__}")

    # 1) 产物身份必须是 64 hex，理由见模块 docstring（下游拿它拼 input_unit_id）。
    artifact_id = _require_hex64(artifact.get("artifact_id"), "artifact_id")

    # 5) 空 chunks → 拒绝。空产物会让 content_hash 退化成"空串的哈希"，
    #    任何两个空产物都"绑定成功"，这是最常见的假绿来源。
    chunks = artifact.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ArtifactBindingError("chunks 必须是非空列表")

    raw_doc_id = artifact.get("document_id")
    document_id = raw_doc_id.strip() if isinstance(raw_doc_id, str) and raw_doc_id.strip() else None
    if raw_doc_id is not None and document_id is None:
        raise ArtifactBindingError("document_id 给了但不是非空字符串")

    docs = []
    manifest = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise ArtifactBindingError(f"chunk[{index}] 必须是 dict")

        # 2a) text 必须非空。保留原样（不 strip）：引用的正文必须逐字节等于产物正文，
        #     否则 quote_hash 对不上原文。
        text = chunk.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ArtifactBindingError(f"chunk[{index}] 的 text 为空或不是字符串")

        # 2b) locator 必须存在且非空。
        locator = _check_locator(chunk.get("locator"), index)

        # 3) 自带哈希必须与重算的 text 哈希一致（防止产物在传递途中被改）。
        #    带了就严格比对；带了个不像哈希的值同样拒绝 —— 无法校验等于没校验。
        text_hash = _sha256(text)
        for key in _CHUNK_HASH_KEYS:
            if key in chunk and chunk[key] is not None:
                declared = _require_hex64(chunk[key], f"chunk[{index}].{key}")
                if declared != text_hash:
                    raise ArtifactBindingError(
                        f"chunk[{index}] 的 {key} 与正文不符：声明 {declared}，重算 {text_hash}")

        # 4) file_id 缺省用 document_id；两者都没有就没法做来源收口。
        file_id = chunk.get("file_id")
        if isinstance(file_id, str) and file_id.strip():
            file_id = file_id.strip()
        elif file_id is None or (isinstance(file_id, str) and not file_id.strip()):
            if document_id is None:
                raise ArtifactBindingError(
                    f"chunk[{index}] 缺少 file_id 且 artifact 没有 document_id 可回落")
            file_id = document_id
        else:
            raise ArtifactBindingError(f"chunk[{index}] 的 file_id 必须是字符串")

        docs.append({"file_id": file_id, "text": text,
                     "locator": locator, "artifact_id": artifact_id})
        manifest.append({"locator": _locator_key(locator), "text_sha256": text_hash})

    content_hash = _sha256(json.dumps(
        {"schema": CONTENT_SPEC, "chunks": manifest},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    return {"artifact_id": artifact_id, "document_id": document_id,
            "content_hash": content_hash, "docs": docs}


def assert_same_artifact(a, b):
    """断言两份绑定指向同一份产物；不同就抛错，绝不返回 True/False 让调用方忽略。

    为什么两个字段都要比：`artifact_id` 是**编号**，`content_hash` 是**内容**。
    同编号不同内容 = 产物被原地改写（编号系统不可信）；
    同内容不同编号 = 重新解析了一次（不算同一产物，引用会指向不同快照）。
    只比其一都会放过一类错配，所以两个都不一致才算通过的反面 —— 任一不同即失败。
    """
    for name, bound in (("a", a), ("b", b)):
        if not isinstance(bound, dict):
            raise ArtifactBindingError(f"{name} 必须是 bind_artifact 的输出（dict）")
        for field in ("artifact_id", "content_hash"):
            if not bound.get(field):
                raise ArtifactBindingError(f"{name} 缺少 {field}，无法比对")

    if a["artifact_id"] != b["artifact_id"]:
        raise ArtifactBindingError(
            f"artifact_id 不同：{a['artifact_id']} vs {b['artifact_id']}（不是同一份解析产物）")
    if a["content_hash"] != b["content_hash"]:
        raise ArtifactBindingError(
            f"content_hash 不同：{a['content_hash']} vs {b['content_hash']}（同一编号下内容已变）")
