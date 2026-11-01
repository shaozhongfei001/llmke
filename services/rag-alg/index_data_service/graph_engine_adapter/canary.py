"""灰度策略：按知识库（KB）决定这个 KB 走全量重建还是增量重建。

为什么灰度要落在"配置"而不是"代码分支"：
- `rebuild()`（全量）与 `rebuild_delta()`（增量）代价差着数量级——增量省掉重新抽取
  已存在的内容；但增量有前提（必须有一份可复用的上一份快照），也有风险（差异算错会
  漏内容）。所以先放一小撮 KB 走增量、其余继续走全量，观察一段再放量。这需要一个
  "谁在灰度里"的名单，名单必须能改，而不是发版。
- **回退不用重启**：名单与模式都放文件里，`load()` 每次调用都重新读盘。出问题时把
  文件改回去（或删掉文件回落到环境变量）下一次判断就生效，既不用重建策略对象，也不用
  重启进程。因此这里**刻意不做缓存**：缓存换来的是"改了配置却没生效"——这类故障最
  难查，而且恰恰会在灰度出事、最需要回退的时候出现。

优先级：**文件 > 环境变量 > 默认**。文件是热改的载体；环境变量是部署期兜底；
两者都没有时 `scope` 为空、`mode` 取 `default` —— 等于"谁都不在灰度里"，这是安全默认
（名单为空 = 全部走全量，已知正确的那条路）。

配错必须停：文件损坏、未知 mode、未知字段一律抛 `CanaryConfigError`（消息带文件路径），
**不静默降级**。因为静默降级会把"灰度"悄悄变成"按默认跑"——出问题时没人知道配置根本
没生效，事后也没法从行为上分辨是"配置没读到"还是"配置生效了但结果一样"。

`describe()` 只输出名单、模式与来源，不含任何密钥类信息（本模块也不读密钥，只读两个
模式名与 KB 标识）。文件路径也不进 `describe()`：路径里可能带运维账号名，报错信息里
有就够定位了。

环境变量：
  LLMKE_CANARY_SCOPE    灰度名单，逗号分隔（如 "kb_1,kb_2"）
  LLMKE_CANARY_MODE     灰度内 KB 用的模式：full / delta
  LLMKE_CANARY_DEFAULT  灰度外（以及 mode 缺省）用的模式，默认 full

配置文件（JSON）：
  {"scope": ["kb_1", "kb_2"], "mode": "delta", "default": "full"}
`scope` 也接受逗号分隔字符串形式。
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple, Union

SCHEMA = "llmke.graph-engine.canary-policy.v1"

MODES = ("full", "delta")
DEFAULT_MODE = "full"

ENV_SCOPE = "LLMKE_CANARY_SCOPE"
ENV_MODE = "LLMKE_CANARY_MODE"
ENV_DEFAULT = "LLMKE_CANARY_DEFAULT"

# 字段名 → 环境变量名：报错时要说清"该改哪一个"，否则运维只能猜
ENV_NAMES = {"scope": ENV_SCOPE, "mode": ENV_MODE, "default": ENV_DEFAULT}

SOURCE_FILE = "file"
SOURCE_ENV = "env"
SOURCE_DEFAULT = "default"
SOURCE_EXPLICIT = "explicit"

_FIELDS = ("scope", "mode", "default")


class CanaryConfigError(ValueError):
    """灰度配置本身有错（文件损坏 / 取值非法 / 字段拼错）：必须停下，不按默认继续跑。"""


def _check_mode(name: str, raw: Any) -> str:
    """校验模式名；错误消息同时给出**允许值**和**原值**（只给"非法"等于让人猜）。"""
    value = raw.strip() if isinstance(raw, str) else raw
    if not isinstance(value, str) or value not in MODES:
        raise ValueError(f"{name} 取值非法：{raw!r}；允许值 {list(MODES)}")
    return value


def _normalize_scope(raw: Any) -> FrozenSet[str]:
    """把名单归一成 frozenset：字符串按逗号切、逐项去空白、天然去重且不可变。"""
    if isinstance(raw, str):
        entries = raw.split(",")
    elif isinstance(raw, (list, tuple, set, frozenset)):
        entries = list(raw)
    else:
        raise ValueError(f"scope 必须是字符串或列表，实际 {type(raw).__name__}：{raw!r}")
    kept = set()
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError(f"scope 元素必须是字符串，实际 {type(entry).__name__}：{entry!r}")
        kb_id = entry.strip()
        if not kb_id:
            # 空串/纯空白是"配错"，不是"不加灰度"：静默跳过会让名单少一个 KB 却不报错，
            # 后续排查只能靠猜（"我以为 kb_1 在灰度里"）。
            raise ValueError(f"scope 含空的 KB 标识：{entry!r}")
        kept.add(kb_id)
    return frozenset(kept)


def _normalize_sources(raw: Any) -> Tuple[Tuple[str, str], ...]:
    """来源记录归一成有序元组（不可变；不进 describe 的输出集合之外）。"""
    if not raw:
        return ()
    items = raw.items() if hasattr(raw, "items") else raw
    return tuple(sorted((str(name), str(label)) for name, label in items))


@dataclass(frozen=True)
class CanaryPolicy:
    """一份灰度策略：不可变值对象（frozen）。改策略 = 造新对象，不是改旧对象。

    不可变不是洁癖：同一份策略会被多个 KB 的请求并发读到，就地改字段会出现
    "一半 KB 按旧名单、一半按新名单"的中间态，而这种中间态在日志里看不出来。
    """

    scope: FrozenSet[str]
    mode: str
    default: str = DEFAULT_MODE
    sources: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        # frozen dataclass 只能在 __post_init__ 里用 object.__setattr__ 归一化字段，
        # 这样构造完的实例一定处于"已校验、已归一"的状态，外部拿不到半成品。
        object.__setattr__(self, "mode", _check_mode("mode", self.mode))
        object.__setattr__(self, "default", _check_mode("default", self.default))
        object.__setattr__(self, "scope", _normalize_scope(self.scope))
        object.__setattr__(self, "sources", _normalize_sources(self.sources))

    def mode_for(self, kb_id: str) -> str:
        """在灰度名单里用 `mode`，否则用 `default`。"""
        return self.mode if kb_id in self.scope else self.default

    def in_canary(self, kb_id: str) -> bool:
        return kb_id in self.scope

    def describe(self) -> Dict[str, Any]:
        """可安全打印/上报的摘要：名单排序后输出，同一份配置每次结果一致。"""
        ordered = sorted(self.scope)          # 排序：便于日志对比与留证，不受 set 哈希序影响
        stored = dict(self.sources)
        return {"schema": SCHEMA, "scope": ordered, "count": len(ordered),
                "mode": self.mode, "default": self.default,
                # 未知来源标 explicit（代码里直接构造的策略没有读取过程可言）
                "sources": {name: stored.get(name, SOURCE_EXPLICIT) for name in _FIELDS}}


def _read_config(path: Union[str, Path]) -> Dict[str, Any]:
    """读文件并做结构校验。任何问题都**带路径抛错**，绝不返回 None 假装"没有文件"。"""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        # 文件存在性检查与实际读取之间被删/权限变化，也走这里：失败就报，不回落
        raise CanaryConfigError(
            f"灰度配置文件读取失败：{path}（{type(exc).__name__}: {exc}）") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        # 给出行列号：手改配置最常见的错就是多/少一个逗号
        raise CanaryConfigError(
            f"灰度配置文件不是合法 JSON：{path}"
            f"（第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}）") from exc
    if not isinstance(data, dict):
        raise CanaryConfigError(
            f"灰度配置文件顶层必须是 JSON 对象：{path}（实际 {type(data).__name__}）")
    unknown = sorted(str(key) for key in data if key not in _FIELDS)
    if unknown:
        # 拼错的字段（如 "scop"）如果被忽略，配置等于没生效而没人知道——这是最坏的一种"绿灯"
        raise CanaryConfigError(
            f"灰度配置文件含未知字段：{path}（{unknown}；允许 {list(_FIELDS)}）")
    return data


def _pick(data: Optional[Dict[str, Any]], env: Mapping[str, str],
          name: str, env_name: str) -> Tuple[Any, str]:
    """按 文件 > 环境变量 取一个字段；都没有返回 (None, default 来源)。

    空/纯空白的变量视为未设置：部署模板里留一个空值是常态，把它当"配了空值"
    会在启动时直接炸，而它显然表达的是"没配"。
    """
    if data is not None and name in data:
        return data[name], SOURCE_FILE
    raw = env.get(env_name)
    if raw is not None and str(raw).strip():
        return raw, SOURCE_ENV
    return None, SOURCE_DEFAULT


def _config_error(name: str, source: str, path: Any, exc: ValueError) -> CanaryConfigError:
    """文件里来的取值错误带路径，环境变量来的带变量名——定位信息必须够用。"""
    if source == SOURCE_FILE:
        return CanaryConfigError(f"灰度配置非法：{path}（{name}：{exc}）")
    return CanaryConfigError(f"灰度环境变量非法（{ENV_NAMES.get(name, name)}）：{exc}")


def load(path: Union[str, Path, None] = None,
         env: Optional[Mapping[str, str]] = None) -> CanaryPolicy:
    """读一份策略：文件 > 环境变量 > 默认。每次调用都重新读盘（热改即生效）。

    `path` 为空（None 或 ""）表示"没有配置文件"；指向的路径不存在则回落到环境变量。
    文件已存在但读不出来（权限/被删的竞态）属于故障，直接报错——见 `_read_config`。
    """
    environ: Mapping[str, str] = os.environ if env is None else env
    # 只在"压根没有文件"时回落环境变量；文件存在却读不出来属于故障（见 _read_config），
    # 否则权限配错会被当成"没配置"，灰度静默按默认跑。
    data = _read_config(path) if path and Path(path).exists() else None

    scope_raw, scope_src = _pick(data, environ, "scope", ENV_SCOPE)
    mode_raw, mode_src = _pick(data, environ, "mode", ENV_MODE)
    default_raw, default_src = _pick(data, environ, "default", ENV_DEFAULT)

    # 先定 default：mode 没配时"取它"，所以缺省语义必须先进位
    if default_raw is None:
        default_value = DEFAULT_MODE
    else:
        try:
            default_value = _check_mode("default", default_raw)
        except ValueError as exc:
            raise _config_error("default", default_src, path, exc) from exc

    if mode_raw is None:
        mode_value = default_value
    else:
        try:
            mode_value = _check_mode("mode", mode_raw)
        except ValueError as exc:
            raise _config_error("mode", mode_src, path, exc) from exc

    if scope_raw is None:
        scope_value: FrozenSet[str] = frozenset()
    else:
        try:
            scope_value = _normalize_scope(scope_raw)
        except ValueError as exc:
            raise _config_error("scope", scope_src, path, exc) from exc

    return CanaryPolicy(scope=scope_value, mode=mode_value, default=default_value,
                        sources=(("scope", scope_src), ("mode", mode_src),
                                 ("default", default_src)))


def choose_rebuild(policy: CanaryPolicy, kb_id: str) -> str:
    """接线点：返回 "full" 就调 `rebuild()`，返回 "delta" 就调 `rebuild_delta()`。

    只做语义化包装，不在这里加第二种判断：灰度决策必须只有一处真值来源，
    否则"名单里写着在灰度"和"实际走了全量"会各说一套，出事时无从对齐。
    """
    return policy.mode_for(kb_id)
