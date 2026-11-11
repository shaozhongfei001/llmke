"""检索读路径的投影切换（legacy / shadow / snapshot），默认 legacy、可逆、按知识库粒度。

为什么用「显式通道名映射」而不是「换基础名再拼接」
--------------------------------------------------
历史实现把**基础名**换成 `v2cand_<kb>`，再由下游用 `"table_chunks_" + base` 拼出表格索引名，
结果是 `table_chunks_v2cand_kb_9`；而写侧（`index_writer._target_name`）产的是
`v2cand_table_chunks_kb_9`。**两边名字不相等**，snapshot 模式一开，表格通道就会静默查空索引。

根因是两者语义不同：读侧「换基础名」= 在通道前缀**之后**插前缀；写侧「整名前缀」= 在
整个索引名**之前**加前缀。只要还靠拼接，就一定有人改错一边。所以这里改成
**显式通道名映射**：`channel_names` 在同处生成全部通道名，读写两侧拿它逐字对拍。

开关
----
- `INGEST_READ_MODE=legacy|shadow|snapshot`（默认 legacy，未知值 fail-closed）；
- `INGEST_READ_PREFIX`（默认 `v2cand`，尾部下划线可有可无，内部统一成 `<prefix>_`）；
- `INGEST_READ_KBS`（可选，逗号分隔）：只有列出的知识库走影子，其余保持 legacy。

三档语义
--------
- `legacy`：全部旧命名空间，行为与改动前逐字一致；
- `shadow`：**返回结果与 legacy 完全相同**（只多报 `shadow_names` 供比对），
  不发第二次查询 —— 真双读比对留 P6（本层不做查询，改查询就属改检索算法）；
- `snapshot`：真的把各通道换成影子名（`v2cand_<完整名>`）。

已知缺口
--------
写侧目前**不产** `table_summary` 影子（`index_writer.build` 只产 text / table 两份计划），
故 `missing_channels=["table_summary"]` 显式声明：snapshot 模式当前只验证正文 + 表格块双通道，
全量切读（`T-D2MD-17`）前必须补齐，否则表格总结会静默空。
"""

import os

MODES = ("legacy", "shadow", "snapshot")
DEFAULT_MODE = "legacy"
DEFAULT_PREFIX = "v2cand"
CHANNELS = ("text", "table_chunks", "table_summary", "faq")
# 写侧不产的影子通道（见模块 docstring「已知缺口」）
MISSING_CHANNELS = ("table_summary",)


def _split(value):
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def _normalize_prefix(prefix):
    """统一成 `<prefix>_`：读侧的 `v2cand` 与写侧的 `v2cand_` 说的是同一件事。"""
    value = (prefix or "").strip()
    if not value:
        return ""
    return value if value.endswith("_") else value + "_"


def _legacy_channel_names(name):
    return {"text": name,
            "table_chunks": f"table_chunks_{name}",
            "table_summary": f"table_summary_{name}",
            "faq": f"faq_{name}"}


def _shadow_channel_names(name, prefix):
    """整名前缀：`v2cand_` + `<通道前缀 + 库名>`，与 `index_writer._target_name` 同口径。"""
    return {channel: f"{prefix}{_legacy_channel_names(name)[channel]}" for channel in CHANNELS}


def resolve(names, mode=None, prefix=None, only=None):
    """返回 (新的基础名列表, 说明)。

    `说明` 用于打点/对照，不含敏感信息；关键字段：
    - `channel_names`：{通道: [每个库对应的实际索引名]}（与传入 `names` 顺序对齐）；
    - `graph_kb`：{实际名: 原库名}，图召回必须用**原库名**（18094 按库目录组织）；
    - `shadow_names`：`shadow` 模式下的影子名（不改返回结果，仅供比对）；
    - `missing_channels`：写侧尚未产出的影子通道。
    """
    names = [n for n in (names or []) if n and n.strip()]
    mode = (mode or os.environ.get("INGEST_READ_MODE") or DEFAULT_MODE).strip().lower()
    if mode not in MODES:
        raise ValueError(f"INGEST_READ_MODE 非法: {mode!r}，允许 {MODES}")

    if mode == "legacy":
        channel_names = {ch: [] for ch in CHANNELS}
        for name in names:
            for ch, value in _legacy_channel_names(name).items():
                channel_names[ch].append(value)
        return list(names), {"mode": "legacy", "switched": [], "kept_legacy": [],
                             "channel_names": channel_names,
                             "graph_kb": {n: n for n in names},
                             "shadow_names": {}, "missing_channels": []}

    raw_prefix = (prefix or os.environ.get("INGEST_READ_PREFIX") or DEFAULT_PREFIX).strip()
    prefix_ = _normalize_prefix(raw_prefix)
    if not prefix_.strip("_"):
        raise ValueError("INGEST_READ_PREFIX 为空，影子模式必须有前缀")
    only_set = set(only if only is not None else _split(os.environ.get("INGEST_READ_KBS")))

    switched, kept = [], []
    channel_names = {ch: [] for ch in CHANNELS}
    shadow_names = {ch: [] for ch in CHANNELS}
    graph_kb = {}
    for name in names:
        use_shadow = not (only_set and name not in only_set)
        legacy_map = _legacy_channel_names(name)
        shadow_map = _shadow_channel_names(name, prefix_)
        picked = shadow_map if use_shadow else legacy_map
        for ch in CHANNELS:
            channel_names[ch].append(picked[ch])
            shadow_names[ch].append(shadow_map[ch])
        graph_kb[picked["text"]] = name
        (switched if use_shadow else kept).append(name)

    info = {"mode": mode, "prefix": prefix_.rstrip("_"),
            "switched": switched, "kept_legacy": kept,
            "channel_names": channel_names,
            "graph_kb": graph_kb,
            "missing_channels": list(MISSING_CHANNELS)}

    if mode == "shadow":
        # 降级语义：不改返回结果，只报影子名供比对（真双读留 P6）
        legacy_names = {ch: [] for ch in CHANNELS}
        for name in names:
            for ch, value in _legacy_channel_names(name).items():
                legacy_names[ch].append(value)
        info["channel_names"] = legacy_names
        info["graph_kb"] = {n: n for n in names}
        info["switched"], info["kept_legacy"] = [], []
        info["shadow_names"] = shadow_names
        return list(names), info

    info["shadow_names"] = {}
    return list(channel_names["text"]), info


def channel_name(channel, name, mode=None, prefix=None):
    """单个库名 → 该通道的实际索引名（二/三级调用点共用，避免各自拼接）。

    `retrieval_table_chunks` 这类已有库名、只知道通道的调用点用它，
    这样全仓只有这一处知道「影子名怎么拼」。
    """
    if channel not in CHANNELS:
        raise ValueError(f"未知通道 {channel!r}，允许 {CHANNELS}")
    _names, info = resolve([name], mode=mode, prefix=prefix)
    return info["channel_names"][channel][0]


def original_kb(name):
    """影子名 → 原库名（图召回用）。非影子名原样返回。

    图库（18094）按库目录组织，`v2cand_kb_9` 不是库名；若把影子名当 kb 传过去，
    图通道会「查不到库」而不是「查旧库」，属于静默空召回。
    """
    prefix_ = _normalize_prefix(
        os.environ.get("INGEST_READ_PREFIX") or DEFAULT_PREFIX)
    text = str(name or "")
    if prefix_ and prefix_.strip("_") and text.startswith(prefix_):
        return text[len(prefix_):]
    return text
