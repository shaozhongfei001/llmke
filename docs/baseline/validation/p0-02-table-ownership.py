#!/usr/bin/env python3
"""P0-02 / D-01 仪器：37 张表分别被哪些服务读写（共库还是分库的判据之一）。

为什么需要：
    P0-02 的 D-01 是"选定共享原库或独立新库"，而设计文档 5.3 的步骤①与④互相矛盾。
    要裁定这件事，至少要先知道：**同一张表是否被多个服务直接读写**。
    若大量表被多服务共用，独立新库就不是"建一套新表"而是"拆共享写"，成本量与风险评估完全不同。

它怎么判定：
    1. DO 归属：解析 `@TableName`，按文件路径取服务名 —— 这是"所有权"；
    2. SQL 触达：在 `*.xml` 中只匹配**表位**（`FROM/JOIN/INTO/UPDATE` 之后的标识符），
       避免 `answer_id` 这类列名误命中（早先的字边界匹配就把 `answer` 误算进 rag-auth-service）；
    3. 交叉：SQL 触达的服务集合 − 属主服务 = 跨服务读写。

它不判定什么：
    - 是否真的共用一个物理库（还需连接串/配置；配置在本仓库里通常不完整）；
    - 读写频率与事务边界；
    - 通过 OpenFeign 间接访问（那是服务调用，不是直接读写表）。

用法：
    python3 docs/baseline/validation/p0-02-table-ownership.py --src <rag-parent> [--only-cross]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def service_of(path: Path) -> str:
    parts = path.parts
    for i, p in enumerate(parts):
        if p == "rag-parent" and i + 1 < len(parts):
            nxt = parts[i + 1]
            if nxt == "tools" and i + 2 < len(parts):
                return "tools/" + parts[i + 2]
            return nxt
    return "unknown"


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"<!--.*?-->", " ", text, flags=re.S)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--only-cross", action="store_true", help="只列跨服务读写的表")
    a = ap.parse_args()
    if not a.src.is_dir():
        print(f"FAIL: 源码目录不存在: {a.src}")
        return 2

    # 1) 表清单与属主
    owner: dict[str, set] = {}
    table_name_re = re.compile(r'@TableName\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
    for f in a.src.rglob("*.java"):
        txt = f.read_text(encoding="utf-8", errors="replace")
        for t in table_name_re.findall(txt):
            owner.setdefault(t, set()).add(service_of(f))
    if not owner:
        print("FAIL: 未解析到任何 @TableName")
        return 2

    # 2) SQL 表位触达
    tables = sorted(owner)
    alt = "|".join(re.escape(t) for t in tables)
    sql_re = re.compile(rf"\b(?:FROM|JOIN|INTO|UPDATE)\s+`?({alt})`?\b", re.I)
    touch: dict[str, set] = {t: set() for t in tables}
    xml_count = 0
    for f in a.src.rglob("*.xml"):
        txt = strip_comments(f.read_text(encoding="utf-8", errors="replace"))
        hits = set(m.group(1) for m in sql_re.finditer(txt))
        if hits:
            xml_count += 1
        for t in hits:
            touch[t].add(service_of(f))

    cross = {t: sorted(touch[t] - owner[t]) for t in tables if touch[t] - owner[t]}
    multi_owner = {t: sorted(v) for t, v in owner.items() if len(v) > 1}

    print(f"表={len(tables)}  含表位 SQL 的 xml={xml_count}  "
          f"多属主表={len(multi_owner)}  跨服务读写的表={len(cross)}")

    if multi_owner:
        print("\n多属主表（同一个 @TableName 出现在多个服务）：")
        for t, v in multi_owner.items():
            print(f"  MULTI_OWNER: {t} -> {', '.join(v)}")

    print(f"\n{'表':32}{'属主服务':28}{'SQL 触达服务'}")
    for t in tables:
        if a.only_cross and not cross.get(t):
            continue
        mark = "  ← CROSS" if cross.get(t) else ""
        print(f"  {t:32}{','.join(sorted(owner[t])):28}{','.join(sorted(touch[t])) or '-'}{mark}")

    print("\n结论: 跨服务读写的表 = 共库耦合的实际范围；"
          "独立新库的迁移成本与这些表直接相关，而不是与 37 张表整体相关。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
