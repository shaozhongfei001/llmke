#!/usr/bin/env python3
"""P0-02 仪器：把「真实 DDL」与「资产台账」做可判定比对。

为什么需要：
    P0-02 的证据要求是"实际 DDL 与实体模型的差异清单"，但仓内只有台账
    （37 表 / 482 字段，`actual_ddl_sha256` 全为 null），没有 DDL。
    等 data-owner 交出 DDL 后，必须有人能一条命令产出该清单，而不是肉眼比对。

它检查什么：
    1. 表集合：台账 37 张 vs DDL 实际有哪些（缺表 / 多表）
    2. 每表列数：台账 model_field_count vs DDL 列数
       ——注意：DO 字段数可能包含非持久化字段（如 serialVersionUID），故列数不等
       只代表"需人工确认"，不自动等价于"错表结构"。默认按差异报，可用
       --ignore-count-drift 降级。
    3. 每表 DDL 指纹：规范化后算 sha256，可直接回填台账的 actual_ddl_sha256
       （--emit-patch 输出 YAML 片段，不自动改文件）
    4. 引擎 / 字符集：从 DDL 尾部选项提取，供人工核对"生产同版本"

它不检查什么（不夸大）：
    - 字段类型、长度、默认值、注释、索引、约束、触发器 —— 台账没有这些基线，
      没有基线就无法判定"差异"，只能列出 DDL 里有什么（--dump-columns）。
    - 字段语义（create_by 到底是用户 ID / 账号 / 姓名）—— 必须人工裁定。

用法：
    python3 docs/baseline/validation/p0-02-ddl-diff.py --ddl /path/to/schema.sql
    ... --ignore-count-drift        # 只把表集合差异视为失败
    ... --emit-patch                # 额外输出台账回填片段
    ... --dump-columns              # 逐表列名与类型（人工核对用）

退出码：0 = 无差异；2 = 有差异（或输入不可解析）。
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "docs/reuse/DATABASE-ASSETS.yaml"
# 字段级基线：来自上游「数据库表结构-字段明细.csv」（由 DO 实体导出），
# 有它才能把比对从"列数"提升到"列名 + 类型 + 可空"。
FIELD_CSV = REPO / "docs/upstream/数据库表结构-字段明细.csv"

CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?([A-Za-z0-9_]+)[`\"']?\s*\(",
    re.IGNORECASE,
)
NON_COLUMN = re.compile(
    r"^(PRIMARY|UNIQUE|KEY|INDEX|CONSTRAINT|FULLTEXT|SPATIAL|FOREIGN|CHECK)\b", re.IGNORECASE)


def split_statements(text: str):
    """按括号深度切出每个 CREATE TABLE 的完整文本（不依赖 SQL 解析器）。"""
    out = []
    for m in CREATE_RE.finditer(text):
        name = m.group(1)
        i = m.end() - 1          # 指向 '('
        depth = 0
        start = m.start()
        while i < len(text):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    # 吃掉分号与尾部选项（ENGINE=... DEFAULT CHARSET=...）
                    j = text.find(";", i)
                    end = (j + 1) if j != -1 else len(text)
                    out.append((name, text[start:end]))
                    i = end
                    break
            i += 1
    return out


def parse_columns(body: str):
    """列出 '(' ... ')' 之间属于列定义的行。"""
    start = body.index("(") + 1
    depth = 1
    i = start
    while i < len(body) and depth:
        if body[i] == "(":
            depth += 1
        elif body[i] == ")":
            depth -= 1
        i += 1
    inner = body[start:i - 1]
    cols = []
    for raw in inner.split("\n"):
        line = raw.strip().rstrip(",")
        if not line:
            continue
        if NON_COLUMN.match(line):
            continue
        m = re.match(r"^[`\"']?([A-Za-z0-9_]+)[`\"']?\s+([A-Za-z]+(?:\([^)]*\))?)", line)
        if m:
            cols.append({
                "name": m.group(1).lower(),
                "type": m.group(2).upper(),
                "nullable": "NOT NULL" not in line.upper(),
            })
    return cols


def options_of(body: str):
    tail = body[body.rfind(")") + 1:]
    engine = re.search(r"ENGINE\s*=\s*(\w+)", tail, re.IGNORECASE)
    charset = re.search(r"(?:DEFAULT\s+)?CHARSET\s*=\s*(\w+)", tail, re.IGNORECASE)
    return (engine.group(1).upper() if engine else None,
            charset.group(1).lower() if charset else None)


def normalize(body: str) -> str:
    """规范化后算指纹：去行尾空白、压缩连续空白、统一换行。

    为什么要规范化：`SHOW CREATE TABLE` 的缩进/换行因客户端而变，
    原样哈希会让"同一张表"产生不同指纹，回填台账后无法复现。
    """
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def load_fields(path: Path):
    import csv
    out: dict[str, dict] = {}
    for r in csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()):
        table = (r.get("表名") or "").strip()
        col = (r.get("字段名") or "").strip().lower()
        if not table or not col:
            continue
        out.setdefault(table, {})[col] = {
            "type": (r.get("SQL类型") or "").upper(),
            "len": (r.get("长度") or "").strip(),
            "nullable": (r.get("可空") or "").strip() == "是",
            "pk": (r.get("主键") or "").strip(),
            "auto": (r.get("自增") or "").strip(),
        }
    return out


def type_of(col: dict) -> str:
    """带长度才算完整类型：VARCHAR(64) 与 VARCHAR(128) 不应视为相同。"""
    ty = col["type"]
    if "(" in ty:
        return ty
    return f"{ty}({col['len']})" if col.get("len") else ty


def load_ledger():
    import yaml
    doc = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    return {it["legacy_table"]: it for it in doc["items"]}, doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ddl", type=Path, required=True, help="含 CREATE TABLE 的 SQL 文件")
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--fields-csv", type=Path, default=FIELD_CSV,
                    help="字段级基线（上游字段明细 CSV）；缺省自动读取")
    ap.add_argument("--ignore-count-drift", action="store_true",
                    help="只把表集合差异判为失败（列数不等仅提示）")
    ap.add_argument("--emit-patch", action="store_true", help="输出台账 actual_ddl_sha256 回填片段")
    ap.add_argument("--dump-columns", action="store_true")
    a = ap.parse_args()

    if not a.ddl.is_file():
        print(f"FAIL: DDL 文件不存在: {a.ddl}")
        return 2
    text = a.ddl.read_text(encoding="utf-8", errors="replace")
    tables = split_statements(text)
    if not tables:
        print("FAIL: 未解析出任何 CREATE TABLE（检查是否为 SHOW CREATE TABLE 输出或建表脚本）")
        return 2

    ledger, _doc = load_ledger()
    actual = {}
    for name, body in tables:
        if name in actual:
            print(f"FAIL: DDL 中重复定义表 {name}")
            return 2
        actual[name] = {"body": body, "cols": parse_columns(body),
                        "opts": options_of(body),
                        "sha": hashlib.sha256(normalize(body).encode()).hexdigest()}

    missing = sorted(set(ledger) - set(actual))
    extra = sorted(set(actual) - set(ledger))

    drift = []
    for name in sorted(set(ledger) & set(actual)):
        want = ledger[name].get("model_field_count")
        got = len(actual[name]["cols"])
        if want is not None and want != got:
            drift.append((name, want, got))

    print(f"DDL 表数={len(actual)}  台账表数={len(ledger)}  "
          f"缺表={len(missing)} 多表={len(extra)} 列数不一致={len(drift)}")
    for n in missing:
        print(f"  MISSING_IN_DDL: {n}（台账 model_field_count={ledger[n].get('model_field_count')}）")
    for n in extra:
        print(f"  EXTRA_IN_DDL:   {n}（DDL 列数={len(actual[n]['cols'])}）")
    for n, want, got in drift:
        print(f"  COUNT_DRIFT:    {n} 台账={want} DDL={got} → 需人工确认"
              f"（DO 可能含非持久化字段）")

    field_base = {}
    if a.fields_csv and Path(a.fields_csv).is_file():
        field_base = load_fields(Path(a.fields_csv))

    col_findings = []
    if field_base:
        for name in sorted(set(field_base) & set(actual)):
            want, got = field_base[name], {c["name"]: c for c in actual[name]["cols"]}
            for col in sorted(set(want) - set(got)):
                col_findings.append(f"MISSING_COLUMN: {name}.{col}（基线 {type_of(want[col])}）")
            for col in sorted(set(got) - set(want)):
                col_findings.append(f"EXTRA_COLUMN:   {name}.{col}（DDL {got[col]['type']}）")
            for col in sorted(set(want) & set(got)):
                w, g = want[col], got[col]
                if type_of(w).replace(" ", "") != g["type"].replace(" ", ""):
                    col_findings.append(
                        f"TYPE_MISMATCH:  {name}.{col} 基线 {type_of(w)} DDL {g['type']}")
                if w["nullable"] != g["nullable"]:
                    wnull = "NULL" if w["nullable"] else "NOT NULL"
                    gnull = "NULL" if g["nullable"] else "NOT NULL"
                    col_findings.append(
                        f"NULL_MISMATCH:  {name}.{col} 基线 {wnull} DDL {gnull}")

    print(f"\n字段级比对：基线表={len(field_base)}  发现差异={len(col_findings)}")
    for f_ in col_findings[:20]:
        print("  " + f_)
    if len(col_findings) > 20:
        print(f"  ...（共 {len(col_findings)} 条，仅显示前 20）")

    if a.dump_columns:
        print("\n逐表列（供人工核对类型/语义）:")
        for n in sorted(actual):
            cols = ", ".join(f"{c['name']}:{c['type']}" for c in actual[n]["cols"])
            engine, charset = actual[n]["opts"]
            print(f"  {n} [{engine or '?'}/{charset or '?'}] {cols}")

    if a.emit_patch:
        print("\n# 台账回填片段（人工粘贴到 docs/reuse/DATABASE-ASSETS.yaml 对应项）")
        for n in sorted(actual):
            print(f"# {n}\n#   actual_ddl_sha256: {actual[n]['sha']}")

    failed = (bool(missing) or bool(extra) or bool(col_findings)
              or (bool(drift) and not a.ignore_count_drift and not field_base))
    if failed:
        verdict = ("FAIL（存在差异，需按上面的清单补齐或裁定）"
                   if not col_findings else
                   f"FAIL（{len(col_findings)} 处字段级差异，见上）")
    elif drift:
        verdict = f"PASS（表集合一致；{len(drift)} 处列数漂移按 --ignore-count-drift 忽略，仍需人工确认）"
    else:
        verdict = "PASS（表集合一致，列数一致）"
    print("\n结论:", verdict)
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
