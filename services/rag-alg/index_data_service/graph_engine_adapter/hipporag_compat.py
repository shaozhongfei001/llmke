"""HippoRAG 中文兼容补丁（**显式偏离上游**，必须记录，不许静默生效）。

上游事实：`hipporag 2.0.0a4` 的 `utils/misc_utils.py:54`

```python
def text_processing(text):
    return re.sub('[^A-Za-z0-9 ]', ' ', text.lower()).strip()
```

它把**所有非 ASCII 字符**替换成空格。中文三元组因此变成
`("", "", "5000")` 甚至 `("", "", "")`——实测 `fact_embedding_store` 18 行全是空主谓。
下游连锁反应：

1. 重排器看到的候选事实是空壳 → 返回 `{}` → `facts_after_rerank=0`；
2. 引擎按设计回退稠密 → `graph_calls=0`；
3. 即使重排成功，图上的实体也全是空串，PPR 没有意义。

所以"图没跑"的根因不是模型不听话，是**上游不支持中文**。

本模块提供一个**可选**补丁：保留 CJK 与全角字符，其余仍归一为空格。用法必须显式：

```python
from graph_engine_adapter.hipporag_compat import install_cjk_text_processing
install_cjk_text_processing()      # 在 import hipporag 之后、index 之前调用
```

不默认安装：默认路径必须与上游一致，否则"我们跑通了"会掩盖上游的真实缺陷。
"""

import re
from typing import Callable, Optional

# 只保留"汉字 + 字母数字"，中文标点/全角括号仍按上游思路清成空格：
# 实体名里混标点会让同一实体分裂成多个节点。
_CJK_RANGES = (
    "\u4e00-\u9fff"      # 基本汉字
    "\u3400-\u4dbf"      # 扩展 A
    "\uf900-\ufaff"      # 兼容汉字
)
_UPSTREAM_PATTERN = "[^A-Za-z0-9 ]"
_CJK_PATTERN = f"[^0-9A-Za-z{_CJK_RANGES} ]"


def cjk_text_processing(text):
    """与上游同构，但保留 CJK；连续空白折叠成一个空格。"""
    if isinstance(text, list):
        return [cjk_text_processing(t) for t in text]
    if not isinstance(text, str):
        text = str(text)
    out = re.sub(_CJK_PATTERN, " ", text.lower())
    return re.sub(r"\s+", " ", out).strip()


def install_cjk_text_processing() -> dict:
    """把补丁装到**两个**命名空间：定义处与 `HippoRAG.py` 的导入副本。

    只改定义处不生效——`HippoRAG.py` 用的是 `from ... import text_processing` 的名字副本。
    返回安装报告，便于在证据里记录"确实改了哪两个位置"。
    """
    import hipporag.utils.misc_utils as misc

    installed = []
    misc.text_processing = cjk_text_processing
    installed.append("hipporag.utils.misc_utils.text_processing")

    # 注意：`import hipporag.HippoRAG as X` 拿到的是**类**（包 __init__ 里重名导出），
    # 必须走 sys.modules 才能拿到真正用 `from ... import *` 的模块命名空间。
    import sys

    hp_mod = sys.modules.get("hipporag.HippoRAG")
    if hp_mod is not None and hasattr(hp_mod, "text_processing"):
        hp_mod.text_processing = cjk_text_processing
        installed.append("hipporag.HippoRAG.text_processing")

    return {"patched": installed, "pattern": _CJK_PATTERN,
            "upstream_pattern": _UPSTREAM_PATTERN,
            "note": "显式偏离上游：上游会清空全部中文事实"}


def is_patched() -> Optional[bool]:
    """True/False=已装/未装；None=环境里没有 hipporag。"""
    import sys

    hp_mod = sys.modules.get("hipporag.HippoRAG")
    if hp_mod is None:
        return None
    fn: Optional[Callable] = getattr(hp_mod, "text_processing", None)
    return fn is cjk_text_processing
