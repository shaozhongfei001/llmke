#!/usr/bin/env python3
"""
Oracle 元数据自动汇总与人工数据字典核对工具
完整实现 oracle_metadata_reconciliation SKILL
"""

import oracledb
import openpyxl
import re
import os
import sys
from datetime import datetime
from collections import defaultdict
from copy import copy
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 配置 — 全部走环境变量（禁止把凭据写进代码/提交）
# ──────────────────────────────────────────────────────────────
ORACLE_HOST = os.getenv("ORACLE_HOST", "")
ORACLE_PORT = int(os.getenv("ORACLE_PORT", "1521"))
ORACLE_SERVICE = os.getenv("ORACLE_SERVICE", "")  # 或使用 ORACLE_SID
ORACLE_USER = os.getenv("ORACLE_USER", "")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")  # 不在日志中打印
ORACLE_SCHEMA = os.getenv("ORACLE_SCHEMA", os.getenv("ORACLE_METADATA_FOCUS_SCHEMA", ""))
# thick 模式客户端路径；留空 = thin 模式。框架不提供任何默认安装路径。
ORACLE_CLIENT_LIB = os.getenv("ORACLE_CLIENT_DIR", "")

# 数据字典文件列表（os.pathsep 分隔；按优先级排序，先出现者覆盖后出现的）
DICT_FILES = [p for p in os.getenv("ORACLE_DICT_FILES", "").split(os.pathsep) if p]

# 输出目录
OUTPUT_DIR = os.getenv("ORACLE_RECONCILE_OUT", "./output/oracle-reconciliation")

_missing = [k for k, v in {
    "ORACLE_HOST": ORACLE_HOST,
    "ORACLE_SERVICE": ORACLE_SERVICE,
    "ORACLE_USER": ORACLE_USER,
    "ORACLE_PASSWORD": ORACLE_PASSWORD,
    "ORACLE_SCHEMA": ORACLE_SCHEMA,
}.items() if not v]
if _missing:
    sys.exit(
        "缺少环境变量: " + ", ".join(_missing)
        + "\n示例: export ORACLE_HOST=… ORACLE_SERVICE=… ORACLE_USER=… ORACLE_PASSWORD=… ORACLE_SCHEMA=…"
        + "\n可选: ORACLE_DICT_FILES='/a.xlsx:/b.xlsx' ORACLE_RECONCILE_OUT=./output"
    )
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 注释永久损坏的表（ZHS16GBK 迁移损坏，字节全为 0x3f）
# 这些表应从最终报告中排除，或单独标记
CORRUPTED_TABLES = set()  # 运行时自动检测填充，也可手动指定

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

EMPTY_VALUES = {"", " ", "-", "N/A", "NA", "无", "暂无", "待补充", None, "null", "NULL"}


# ──────────────────────────────────────────────────────────────
# Oracle 元数据采集
# ──────────────────────────────────────────────────────────────
def _load_readonly_guard():
    """Locate the shared read-only guard (scripts/oracle_metadata/readonly_guard.py).

    Works both in the framework repo and in projects installed via bootstrap
    (.cursor/skills/<skill>/scripts/reconcile.py -> <root>/scripts/oracle_metadata/).
    The reconciliation tool and the catalog gates share ONE guard — fail-closed.
    """
    import importlib.util

    here = Path(__file__).resolve()
    candidates = []
    for up in here.parents:
        candidates.append(up / "scripts" / "oracle_metadata" / "readonly_guard.py")
        candidates.append(up / "readonly_guard.py")
    for cand in candidates:
        if cand.is_file():
            spec = importlib.util.spec_from_file_location("readonly_guard", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit(
        "ERROR: shared read-only guard not found (expected "
        "scripts/oracle_metadata/readonly_guard.py). Re-run bootstrap."
    )


def connect_oracle(driver=None):
    """连接 Oracle 数据库（强制只读：与 Catalog 共用同一套 Guard）。

    SET TRANSACTION READ ONLY 建立失败 → 关闭连接并非零退出；
    没有任何"仅策略约束"的软通过路径。
    """
    guard = _load_readonly_guard()
    params = {
        "host": ORACLE_HOST,
        "port": ORACLE_PORT,
        "service": ORACLE_SERVICE,
        "user": ORACLE_USER,
        "password": ORACLE_PASSWORD,
        "lib_dir": ORACLE_CLIENT_LIB,
    }
    ctx = guard.readonly_session(
        driver=driver,
        connect_params=params,
        evidence_dir=Path(OUTPUT_DIR),
    )
    conn = ctx.__enter__()
    conn._readonly_guard_ctx = ctx
    # 验证 schema
    cur = conn.cursor()
    guard.execute_readonly(
        cur, "SELECT COUNT(*) FROM all_tables WHERE owner = :schema",
        {"schema": ORACLE_SCHEMA},
    )
    count = cur.fetchone()[0]
    cur.close()
    print(f"[Oracle] 连接成功(只读已验证), Schema={ORACLE_SCHEMA}, 表数={count}")
    return conn


def fetch_oracle_tables(conn):
    """采集表级元数据"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.owner AS schema_name,
            t.table_name,
            c.comments AS table_comment,
            t.tablespace_name,
            t.num_rows,
            t.last_analyzed,
            o.created AS created_time,
            o.last_ddl_time
        FROM all_tables t
        LEFT JOIN all_tab_comments c
            ON t.owner = c.owner AND t.table_name = c.table_name
        LEFT JOIN all_objects o
            ON t.owner = o.owner AND t.table_name = o.object_name AND o.object_type = 'TABLE'
        WHERE t.owner = :schema
        ORDER BY t.table_name
    """, schema=ORACLE_SCHEMA)

    tables = {}
    for row in cur.fetchall():
        tname = row[1]
        tables[tname] = {
            "schema_name": row[0],
            "table_name": tname,
            "table_comment": row[2],
            "tablespace_name": row[3],
            "num_rows": row[4],
            "last_analyzed": row[5],
            "created_time": row[6],
            "last_ddl_time": row[7],
        }
    cur.close()
    print(f"[Oracle] 采集 {len(tables)} 张表")
    return tables


def fetch_oracle_columns(conn):
    """采集字段级元数据"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.owner, c.table_name, c.column_name, c.column_id,
            c.data_type, c.data_length, c.data_precision, c.data_scale,
            c.nullable, c.data_default, cc.comments
        FROM all_tab_columns c
        LEFT JOIN all_col_comments cc
            ON c.owner = cc.owner AND c.table_name = cc.table_name AND c.column_name = cc.column_name
        WHERE c.owner = :schema
        ORDER BY c.table_name, c.column_id
    """, schema=ORACLE_SCHEMA)

    columns = defaultdict(list)
    for row in cur.fetchall():
        columns[row[1]].append({
            "column_name": row[2],
            "column_id": row[3],
            "data_type": row[4],
            "data_length": row[5],
            "data_precision": row[6],
            "data_scale": row[7],
            "nullable": row[8],
            "default_value": row[9],
            "column_comment": row[10],
        })
    cur.close()
    total = sum(len(v) for v in columns.values())
    print(f"[Oracle] 采集 {len(columns)} 张表, {total} 个字段")
    return dict(columns)


def fetch_oracle_primary_keys(conn):
    """采集主键信息"""
    cur = conn.cursor()
    cur.execute("""
        SELECT acc.table_name, acc.column_name, acc.position, ac.constraint_name
        FROM all_constraints ac
        JOIN all_cons_columns acc
            ON ac.owner = acc.owner AND ac.constraint_name = acc.constraint_name
        WHERE ac.owner = :schema AND ac.constraint_type = 'P'
        ORDER BY acc.table_name, acc.position
    """, schema=ORACLE_SCHEMA)

    pks = defaultdict(list)
    for row in cur.fetchall():
        pks[row[0]].append({"column_name": row[1], "position": row[2], "constraint_name": row[3]})
    cur.close()
    print(f"[Oracle] 采集 {len(pks)} 张表的主键")
    return dict(pks)


def fetch_oracle_foreign_keys(conn):
    """采集外键信息"""
    cur = conn.cursor()
    cur.execute("""
        SELECT fk.table_name, fkc.column_name, pk.table_name, pkc.column_name,
               fk.constraint_name
        FROM all_constraints fk
        JOIN all_cons_columns fkc
            ON fk.owner = fkc.owner AND fk.constraint_name = fkc.constraint_name
        JOIN all_constraints pk
            ON fk.r_owner = pk.owner AND fk.r_constraint_name = pk.constraint_name
        JOIN all_cons_columns pkc
            ON pk.owner = pkc.owner AND pk.constraint_name = pkc.constraint_name
            AND fkc.position = pkc.position
        WHERE fk.owner = :schema AND fk.constraint_type = 'R'
        ORDER BY fk.table_name, fkc.position
    """, schema=ORACLE_SCHEMA)

    fks = defaultdict(list)
    for row in cur.fetchall():
        fks[row[0]].append({
            "child_column": row[1],
            "parent_table": row[2],
            "parent_column": row[3],
            "constraint_name": row[4],
        })
    cur.close()
    print(f"[Oracle] 采集 {len(fks)} 张表的外键")
    return dict(fks)


def fetch_oracle_indexes(conn):
    """采集索引信息"""
    cur = conn.cursor()
    cur.execute("""
        SELECT i.table_name, i.index_name, i.uniqueness, ic.column_name, ic.column_position
        FROM all_indexes i
        JOIN all_ind_columns ic
            ON i.owner = ic.index_owner AND i.index_name = ic.index_name
        WHERE i.owner = :schema
        ORDER BY i.table_name, i.index_name, ic.column_position
    """, schema=ORACLE_SCHEMA)

    indexes = defaultdict(lambda: defaultdict(list))
    for row in cur.fetchall():
        indexes[row[0]][row[1]].append({
            "uniqueness": row[2],
            "column_name": row[3],
            "column_position": row[4],
        })
    cur.close()
    tbl_count = len(indexes)
    idx_count = sum(len(v) for v in indexes.values())
    print(f"[Oracle] 采集 {tbl_count} 张表的 {idx_count} 个索引")
    return dict(indexes)


# ──────────────────────────────────────────────────────────────
# 人工数据字典解析
# ──────────────────────────────────────────────────────────────
def normalize_name(value):
    if value is None:
        return None
    s = str(value).strip().upper()
    # 全角转半角
    s = s.replace("\uff08", "(").replace("\uff09", ")").replace("\uff1a", ":")
    return s


def is_empty(value):
    return value is None or str(value).strip().upper() in EMPTY_VALUES


def parse_data_type(raw_type):
    """标准化数据类型"""
    if is_empty(raw_type):
        return None, None, None, None
    raw = str(raw_type).strip().upper()
    # 提取 type, length, precision, scale
    # VARCHAR2(15), NUMBER(16,2), INTEGER, DATE, etc.
    m = re.match(r"^(\w+?)(?:\((\d+)(?:,(\d+))?\))?$", raw)
    if not m:
        return raw, None, None, None
    dtype = m.group(1)
    length = int(m.group(2)) if m.group(2) else None
    precision = int(m.group(3)) if m.group(3) else None
    scale = None
    return dtype, length, precision, scale


def parse_dict_file_1(filepath):
    """
    解析: 数据仓库数据ACRM相关数据字典.xlsx
    - 清单 sheet: 表级信息
    - 每个表 sheet: 字段级信息
    """
    wb = openpyxl.load_workbook(filepath, data_only=True)
    tables = {}  # table_name -> table_comment
    columns = defaultdict(list)  # table_name -> [col_info]

    # 1. 读取清单 sheet
    ws = wb["清单"] if "清单" in wb.sheetnames else None
    if ws:
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[1] is not None:  # B column = 序号
                schema = str(row[2]).strip() if row[2] else None
                tname = str(row[3]).strip() if row[3] else None
                comment = str(row[4]).strip() if row[4] else None
                if tname:
                    tables[tname] = comment

    # 2. 读取每个表 sheet
    for sheet_name in wb.sheetnames:
        if sheet_name == "清单":
            continue
        ws = wb[sheet_name]
        if not ws:
            continue
        tname = normalize_name(sheet_name)

        # Find header row (row with 'ID' or '列ID名')
        header_row = None
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), 1):
            vals = [str(v).strip() if v else "" for v in row]
            if "列ID名" in vals or "ID" in [str(v).strip() if v else "" for v in row[:3]]:
                header_row = i
                break

        if header_row is None:
            continue

        # Parse column data starting from header_row + 1
        ws2 = wb[sheet_name]
        for row in ws2.iter_rows(min_row=header_row + 1, values_only=True):
            col_id = row[0]  # A: 列ID
            col_name = row[1]  # B: 列ID名
            col_comment = row[2]  # C: 列中文名
            col_type = row[3]  # D: 字段类型
            is_pk = row[4]  # E: 是否主键
            nullable = row[5]  # F: 是否为空
            remark = row[6] if len(row) > 6 else None  # G: 备注

            if col_name is None:
                continue

            dtype, length, precision, scale = parse_data_type(col_type)
            columns[tname].append({
                "column_name": normalize_name(col_name),
                "column_id": int(col_id) if col_id is not None else len(columns[tname]) + 1,
                "column_comment": str(col_comment).strip() if col_comment else None,
                "data_type": dtype,
                "data_length": length,
                "data_precision": precision,
                "data_scale": scale,
                "is_primary_key": bool(is_pk and str(is_pk).strip() in ("是", "Y", "YES", "主键", "PK")),
                "nullable": str(nullable).strip() if nullable else None,
                "remark": str(remark).strip() if remark else None,
            })

    wb.close()
    print(f"[Dict1] 解析 {len(tables)} 张表, {sum(len(v) for v in columns.values())} 个字段")
    return dict(tables), dict(columns)


def parse_dict_file_2(filepath):
    """
    解析: DICT_ACRM数据挖掘前期分析数据模型_V1.xlsx
    各分类 sheet (人口统计学, 持有产品, etc.)
    """
    tables = {}
    columns = defaultdict(list)

    wb = openpyxl.load_workbook(filepath, data_only=True)
    for sheet_name in wb.sheetnames:
        if sheet_name in ("系统设计工作分析", "数据分析模型-目录", "sql"):
            continue
        ws = wb[sheet_name]
        if not ws:
            continue

        # Try to find table name and columns
        # Structure varies, look for rows with column-like data
        table_name = None
        col_id = 0

        for row in ws.iter_rows(min_row=1, values_only=True):
            vals = list(row)
            # Look for table name indicator
            for v in vals:
                if v and isinstance(v, str) and re.match(r"^S\d{2}_\w+$", v.strip().upper()):
                    table_name = normalize_name(v)
                    break

            if table_name:
                col_id += 1
                # Try to extract column info from row
                # Typically: col_name, col_comment, data_type
                col_name = vals[1] if len(vals) > 1 else None
                col_comment = vals[2] if len(vals) > 2 else None
                col_type = vals[3] if len(vals) > 3 else None

                if col_name and not is_empty(col_name):
                    dtype, length, precision, scale = parse_data_type(col_type)
                    columns[table_name].append({
                        "column_name": normalize_name(col_name),
                        "column_id": col_id,
                        "column_comment": str(col_comment).strip() if col_comment else None,
                        "data_type": dtype,
                        "data_length": length,
                        "data_precision": precision,
                        "data_scale": scale,
                    })
                    if table_name not in tables:
                        tables[table_name] = sheet_name

    wb.close()
    print(f"[Dict2] 解析 {len(tables)} 张表, {sum(len(v) for v in columns.values())} 个字段")
    return dict(tables), dict(columns)


def parse_dict_file_3(filepath):
    """
    解析: DICT_ACRM系统基础表字段级分析.xlsx
    字段级分析明细详情 sheet
    """
    tables = {}
    columns = defaultdict(list)

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb["字段级分析明细详情"] if "字段级分析明细详情" in wb.sheetnames else None
    if not ws:
        wb.close()
        print(f"[Dict3] Sheet '字段级分析明细详情' 不存在")
        return {}, {}

    # Row 2 has headers
    # A=表序号, B=数据平台源字段名, C=字段序号, D=源系统表名, E=源表中文名,
    # F=源系统字段名, H=源字段中文名, I=源系统数据类型, J=允许NULL标志, K=默认值, ...

    current_table = None
    current_table_comment = None
    col_id = 0

    for row in ws.iter_rows(min_row=3, values_only=True):
        # A: 表序号 (new table starts here)
        if row[0] is not None and isinstance(row[0], (int, float)):
            new_table_seq = int(row[0])

        # D: 源系统表名 (e.g. OMDATA.S01_FFHZ)
        table_ref = row[3] if len(row) > 3 else None
        if table_ref and not is_empty(table_ref):
            # Extract table name from "OMDATA.S01_FFHZ/OMDATA.S07_FFHZ"
            ref_str = str(table_ref).strip()
            # Take first part before /
            parts = ref_str.split("/")
            first_part = parts[0].strip()
            if "." in first_part:
                extracted = first_part.split(".")[-1]  # Get table name after schema
            else:
                extracted = first_part
            new_table = normalize_name(extracted)
            if new_table != current_table:
                current_table = new_table
                current_table_comment = str(row[4]).strip() if len(row) > 4 and row[4] else None
                tables[current_table] = current_table_comment
                col_id = 0

        # F: 源系统字段名
        col_name = row[5] if len(row) > 5 else None
        if col_name and not is_empty(col_name) and current_table:
            col_id += 1
            col_comment = row[7] if len(row) > 7 else None  # H: 源字段中文名
            col_type = row[8] if len(row) > 8 else None  # I: 源系统数据类型
            nullable = row[9] if len(row) > 9 else None  # J: 允许NULL标志
            default_val = row[10] if len(row) > 10 else None  # K: 默认值
            sensitive = row[11] if len(row) > 11 else None  # L: 敏感字段标志

            dtype, length, precision, scale = parse_data_type(col_type)
            columns[current_table].append({
                "column_name": normalize_name(col_name),
                "column_id": col_id,
                "column_comment": str(col_comment).strip() if col_comment else None,
                "data_type": dtype,
                "data_length": length,
                "data_precision": precision,
                "data_scale": scale,
                "nullable": str(nullable).strip() if nullable else None,
                "default_value": str(default_val).strip() if default_val else None,
                "sensitive_flag": bool(sensitive and str(sensitive).strip() == "Y"),
            })

    wb.close()
    print(f"[Dict3] 解析 {len(tables)} 张表, {sum(len(v) for v in columns.values())} 个字段")
    return dict(tables), dict(columns)


def merge_dictionary(dict_results):
    """合并多个数据字典的结果，字段级以 column_name 为 key 去重"""
    merged_tables = {}
    merged_columns = defaultdict(list)
    seen_columns = set()  # (table_name, column_name)

    for tables, columns in dict_results:
        for tname, comment in tables.items():
            if tname not in merged_tables:
                merged_tables[tname] = comment

        for tname, cols in columns.items():
            for col in cols:
                key = (tname, col["column_name"])
                if key not in seen_columns:
                    seen_columns.add(key)
                    merged_columns[tname].append(col)

    print(f"[Dict Merge] 合并后 {len(merged_tables)} 张表, {sum(len(v) for v in merged_columns.values())} 个字段")
    return merged_tables, dict(merged_columns)


# ──────────────────────────────────────────────────────────────
# 敏感字段识别
# ──────────────────────────────────────────────────────────────
SENSITIVE_KEYWORDS = {
    "id_card": ["ID_CARD", "IDCARD", "CERT_NO", "CERTIFICATE_NO", "身份证", "证件号", "SFZH"],
    "phone": ["PHONE", "MOBILE", "TEL", "手机号", "电话", "DH", "SJH"],
    "bank_card": ["BANK_CARD", "CARD_NO", "ACCOUNT_NO", "银行卡", "账号", "ZH", "KHH"],
    "password": ["PASSWORD", "PASSWD", "PWD", "密码", "口令", "MM"],
    "address": ["ADDRESS", "ADDR", "地址", "DZ", "JZDZ"],
    "email": ["EMAIL", "MAIL", "邮箱", "YX"],
}


def detect_sensitive(col_name, col_comment):
    """检测敏感字段"""
    name_upper = (col_name or "").upper()
    comment = (col_comment or "").upper()
    for stype, keywords in SENSITIVE_KEYWORDS.items():
        for kw in keywords:
            if kw.upper() in name_upper or kw in comment:
                return True, stype
    return False, None


# ──────────────────────────────────────────────────────────────
# 比对与调和
# ──────────────────────────────────────────────────────────────
def compare_and_reconcile(oracle_tables, oracle_columns, oracle_pks, oracle_fks, oracle_indexes,
                          dict_tables, dict_columns):
    """比对 Oracle 元数据与人工数据字典，生成最终结果"""

    final_rows = []
    comparison_rows = []
    all_tables = set(list(oracle_tables.keys()) + list(dict_tables.keys()))

    stats = {
        "oracle_table_count": len(oracle_tables),
        "dictionary_table_count": len(dict_tables),
        "oracle_column_count": 0,
        "dictionary_column_count": 0,
        "matched_column_count": 0,
        "mismatch_column_count": 0,
        "only_in_oracle_count": 0,
        "only_in_dictionary_count": 0,
        "sensitive_field_count": 0,
    }

    for tname in sorted(all_tables):
        in_oracle = tname in oracle_tables
        in_dict = tname in dict_tables

        # Table-level comparison
        if in_oracle and not in_dict:
            comparison_rows.append({
                "table_name": tname,
                "diff_type": "ONLY_IN_ORACLE",
                "oracle_value": oracle_tables[tname].get("table_comment", ""),
                "dictionary_value": None,
                "final_value": oracle_tables[tname].get("table_comment", ""),
                "confidence_score": 0.90,
                "recommendation": "建议在人工数据字典中补充该表",
            })
        elif not in_oracle and in_dict:
            comparison_rows.append({
                "table_name": tname,
                "diff_type": "ONLY_IN_DICTIONARY",
                "oracle_value": None,
                "dictionary_value": dict_tables.get(tname),
                "final_value": None,
                "confidence_score": 0.30,
                "recommendation": "Oracle中不存在该表，请确认是否为历史表、设计表或错误",
            })

        # Get table comment for final output
        table_comment = None
        if in_oracle and oracle_tables[tname].get("table_comment"):
            table_comment = oracle_tables[tname]["table_comment"]
        elif in_dict and dict_tables.get(tname):
            table_comment = dict_tables[tname]

        # Column-level processing
        ora_cols = {c["column_name"]: c for c in oracle_columns.get(tname, [])}
        dic_cols = {c["column_name"]: c for c in dict_columns.get(tname, [])}
        all_col_names = set(list(ora_cols.keys()) + list(dic_cols.keys()))

        stats["oracle_column_count"] += len(ora_cols)
        stats["dictionary_column_count"] += len(dic_cols)

        for cname in sorted(all_col_names, key=lambda x: ora_cols.get(x, dic_cols.get(x, {})).get("column_id", 999)):
            ora_col = ora_cols.get(cname)
            dic_col = dic_cols.get(cname)

            # PK lookup
            is_pk = False
            pk_pos = None
            if in_oracle:
                for pk in oracle_pks.get(tname, []):
                    if pk["column_name"] == cname:
                        is_pk = True
                        pk_pos = pk["position"]
                        break

            # FK lookup
            is_fk = False
            ref_table = None
            ref_col = None
            if in_oracle:
                for fk in oracle_fks.get(tname, []):
                    if fk["child_column"] == cname:
                        is_fk = True
                        ref_table = fk["parent_table"]
                        ref_col = fk["parent_column"]
                        break

            # Index lookup
            idx_names = []
            if in_oracle:
                for idx_name, idx_cols in oracle_indexes.get(tname, {}).items():
                    for ic in idx_cols:
                        if ic["column_name"] == cname:
                            idx_names.append(f"{idx_name}({ic['uniqueness']})")
                            break

            # Build final row
            row = {}
            if ora_col and dic_col:
                # Both exist - compare and reconcile
                row["schema_name"] = ora_col.get("schema_name") or ORACLE_SCHEMA
                row["table_name"] = tname
                row["final_table_comment"] = table_comment
                row["column_name"] = cname
                row["column_id"] = ora_col.get("column_id")

                # Structural info from Oracle
                row["data_type"] = ora_col.get("data_type")
                row["data_length"] = ora_col.get("data_length")
                row["data_precision"] = ora_col.get("data_precision")
                row["data_scale"] = ora_col.get("data_scale")
                row["nullable"] = ora_col.get("nullable")
                row["default_value"] = ora_col.get("default_value")

                # Business semantics from dict (if not empty)
                row["final_column_comment"] = (
                    dic_col.get("column_comment")
                    if not is_empty(dic_col.get("column_comment"))
                    else ora_col.get("column_comment")
                )

                # PK/FK/Index
                row["is_primary_key"] = is_pk
                row["primary_key_position"] = pk_pos
                row["is_foreign_key"] = is_fk
                row["referenced_table"] = ref_table
                row["referenced_column"] = ref_col
                row["index_names"] = ", ".join(idx_names) if idx_names else None

                # Additional dict fields
                row["business_meaning"] = dic_col.get("business_meaning")
                row["value_range"] = dic_col.get("value_range")
                row["standard_code"] = dic_col.get("standard_code")
                row["source_system"] = dic_col.get("source_system")
                row["owner"] = dic_col.get("owner")

                # Diff detection
                diffs = []
                if ora_col.get("data_type") != dic_col.get("data_type") and not is_empty(dic_col.get("data_type")):
                    diffs.append("DATA_TYPE_MISMATCH")
                if ora_col.get("data_length") != dic_col.get("data_length") and dic_col.get("data_length") is not None:
                    diffs.append("DATA_LENGTH_MISMATCH")

                if not diffs:
                    row["diff_status"] = "MATCHED"
                    row["confidence_score"] = 1.0
                    row["final_source"] = "ORACLE_AND_DICTIONARY_MATCH"
                    row["recommendation"] = "无需处理"
                    stats["matched_column_count"] += 1
                else:
                    row["diff_status"] = "; ".join(diffs)
                    row["confidence_score"] = 0.85
                    row["final_source"] = "ORACLE_STRUCTURAL_OVERRIDE"
                    row["recommendation"] = "类型/长度不一致，已以Oracle为准，建议更新人工字典"
                    stats["mismatch_column_count"] += 1

                # Add comparison record
                for diff in diffs:
                    comparison_rows.append({
                        "table_name": tname,
                        "column_name": cname,
                        "diff_type": diff,
                        "oracle_value": str(ora_col.get(diff.split("_")[0].lower(), "")),
                        "dictionary_value": str(dic_col.get(diff.split("_")[0].lower(), "")),
                        "final_value": str(ora_col.get(diff.split("_")[0].lower(), "")),
                        "final_source": "ORACLE",
                        "confidence_score": 0.85,
                        "recommendation": "已以Oracle为准",
                    })

            elif ora_col and not dic_col:
                # Only in Oracle
                row["schema_name"] = ORACLE_SCHEMA
                row["table_name"] = tname
                row["final_table_comment"] = table_comment
                row["column_name"] = cname
                row["column_id"] = ora_col.get("column_id")
                row["data_type"] = ora_col.get("data_type")
                row["data_length"] = ora_col.get("data_length")
                row["data_precision"] = ora_col.get("data_precision")
                row["data_scale"] = ora_col.get("data_scale")
                row["nullable"] = ora_col.get("nullable")
                row["default_value"] = ora_col.get("default_value")
                row["final_column_comment"] = ora_col.get("column_comment")
                row["is_primary_key"] = is_pk
                row["primary_key_position"] = pk_pos
                row["is_foreign_key"] = is_fk
                row["referenced_table"] = ref_table
                row["referenced_column"] = ref_col
                row["index_names"] = ", ".join(idx_names) if idx_names else None
                row["diff_status"] = "ONLY_IN_ORACLE"
                row["confidence_score"] = 0.90
                row["final_source"] = "ORACLE_ONLY"
                row["recommendation"] = "建议补充人工数据字典"
                stats["only_in_oracle_count"] += 1

            elif dic_col and not ora_col:
                # Only in dictionary - include but mark
                row["schema_name"] = None
                row["table_name"] = tname
                row["final_table_comment"] = table_comment
                row["column_name"] = cname
                row["column_id"] = dic_col.get("column_id")
                row["data_type"] = dic_col.get("data_type")
                row["data_length"] = dic_col.get("data_length")
                row["data_precision"] = dic_col.get("data_precision")
                row["data_scale"] = dic_col.get("data_scale")
                row["nullable"] = dic_col.get("nullable")
                row["default_value"] = dic_col.get("default_value")
                row["final_column_comment"] = dic_col.get("column_comment")
                row["is_primary_key"] = dic_col.get("is_primary_key", False)
                row["primary_key_position"] = None
                row["is_foreign_key"] = False
                row["referenced_table"] = None
                row["referenced_column"] = None
                row["index_names"] = None
                row["diff_status"] = "ONLY_IN_DICTIONARY"
                row["confidence_score"] = 0.30
                row["final_source"] = "DICTIONARY_ONLY"
                row["recommendation"] = "Oracle中不存在，请确认是否为历史字段、设计字段或错误"
                stats["only_in_dictionary_count"] += 1

            # Detect corrupted comments (all question marks from charset mismatch)
            comment = row.get("final_column_comment")
            if comment and set(str(comment).strip()) == {"?"} and len(str(comment).strip()) >= 2:
                row["final_source"] = "DICTIONARY_COMMENT_FALLBACK"
                row["diff_status"] = f"{row['diff_status']}; COMMENT_CORRUPTED_IN_ORACLE"
                row["recommendation"] = "Oracle注释已损坏(字符集迁移问题)，请从人工字典补充"
                if "corrupted_comment_count" not in stats:
                    stats["corrupted_comment_count"] = 0
                stats["corrupted_comment_count"] += 1

            # Sensitive field detection
            sens_flag, sens_type = detect_sensitive(cname, row.get("final_column_comment"))
            row["sensitive_flag"] = sens_flag
            row["sensitive_type"] = sens_type
            if sens_flag:
                stats["sensitive_field_count"] += 1

            # Additional business fields from dict
            if dic_col:
                row["business_meaning"] = row.get("business_meaning") or dic_col.get("business_meaning")
                row["value_range"] = row.get("value_range") or dic_col.get("value_range")
                row["standard_code"] = row.get("standard_code") or dic_col.get("standard_code")
                row["source_system"] = row.get("source_system") or dic_col.get("source_system")
                row["owner"] = row.get("owner") or dic_col.get("owner")

            final_rows.append(row)

    stats["final_table_count"] = len([r for r in final_rows if r["table_name"]])
    stats["final_column_count"] = len(final_rows)

    return final_rows, comparison_rows, stats


# ──────────────────────────────────────────────────────────────
# 输出报告
# ──────────────────────────────────────────────────────────────
FINAL_HEADERS = [
    "schema_name", "table_name", "final_table_comment", "column_name", "column_id",
    "final_column_comment", "data_type", "data_length", "data_precision", "data_scale",
    "nullable", "default_value", "is_primary_key", "primary_key_position",
    "is_foreign_key", "referenced_table", "referenced_column", "index_names",
    "business_meaning", "value_range", "standard_code", "source_system", "owner",
    "final_source", "diff_status", "confidence_score", "recommendation",
    "sensitive_flag", "sensitive_type",
]


def write_final_metadata(final_rows):
    """输出最终核准元数据 xlsx"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "核准元数据"

    # Write header
    for col_idx, header in enumerate(FINAL_HEADERS, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = openpyxl.styles.Font(bold=True)

    # Write data
    for row_idx, row_data in enumerate(final_rows, 2):
        for col_idx, header in enumerate(FINAL_HEADERS, 1):
            val = row_data.get(header)
            ws.cell(row=row_idx, column=col_idx, value=val)

    outpath = os.path.join(OUTPUT_DIR, f"final_reconciled_metadata_{ORACLE_SCHEMA}_{TIMESTAMP}.xlsx")
    wb.save(outpath)
    wb.close()
    print(f"[Output] 核准元数据: {outpath} ({len(final_rows)} 行)")
    return outpath


def write_comparison_report(comparison_rows, stats, final_rows):
    """输出差异报告 xlsx"""
    wb = openpyxl.Workbook()

    # Sheet 1: Summary
    ws1 = wb.active
    ws1.title = "Summary"
    ws1.cell(row=1, column=1, value="指标").font = openpyxl.styles.Font(bold=True)
    ws1.cell(row=1, column=2, value="值").font = openpyxl.styles.Font(bold=True)
    r = 2
    for key, val in stats.items():
        ws1.cell(row=r, column=1, value=key)
        ws1.cell(row=r, column=2, value=val)
        r += 1

    # Sheet 2: Table Differences
    ws2 = wb.create_sheet("表级差异")
    tbl_headers = ["table_name", "diff_type", "oracle_value", "dictionary_value",
                   "final_value", "confidence_score", "recommendation"]
    for col_idx, h in enumerate(tbl_headers, 1):
        ws2.cell(row=1, column=col_idx, value=h).font = openpyxl.styles.Font(bold=True)
    tbl_rows = [r for r in comparison_rows if "column_name" not in r]
    for row_idx, rdata in enumerate(tbl_rows, 2):
        for col_idx, h in enumerate(tbl_headers, 1):
            ws2.cell(row=row_idx, column=col_idx, value=rdata.get(h))

    # Sheet 3: Column Differences
    ws3 = wb.create_sheet("字段级差异")
    col_headers = ["table_name", "column_name", "diff_type", "oracle_value",
                   "dictionary_value", "final_value", "final_source",
                   "confidence_score", "recommendation"]
    for col_idx, h in enumerate(col_headers, 1):
        ws3.cell(row=1, column=col_idx, value=h).font = openpyxl.styles.Font(bold=True)
    col_rows = [r for r in comparison_rows if "column_name" in r]
    for row_idx, rdata in enumerate(col_rows, 2):
        for col_idx, h in enumerate(col_headers, 1):
            ws3.cell(row=row_idx, column=col_idx, value=rdata.get(h))

    # Sheet 4: Only in Oracle columns
    ws4 = wb.create_sheet("仅Oracle存在")
    ws4.cell(row=1, column=1, value="table_name").font = openpyxl.styles.Font(bold=True)
    ws4.cell(row=1, column=2, value="column_name").font = openpyxl.styles.Font(bold=True)
    r = 2
    for row_data in final_rows:
        if row_data.get("diff_status") == "ONLY_IN_ORACLE":
            ws4.cell(row=r, column=1, value=row_data.get("table_name"))
            ws4.cell(row=r, column=2, value=row_data.get("column_name"))
            r += 1

    # Sheet 5: Only in Dictionary columns
    ws5 = wb.create_sheet("仅字典存在")
    ws5.cell(row=1, column=1, value="table_name").font = openpyxl.styles.Font(bold=True)
    ws5.cell(row=1, column=2, value="column_name").font = openpyxl.styles.Font(bold=True)
    r = 2
    for row_data in final_rows:
        if row_data.get("diff_status") == "ONLY_IN_DICTIONARY":
            ws5.cell(row=r, column=1, value=row_data.get("table_name"))
            ws5.cell(row=r, column=2, value=row_data.get("column_name"))
            r += 1

    # Sheet 6: Sensitive Fields
    ws6 = wb.create_sheet("敏感字段")
    ws6.cell(row=1, column=1, value="table_name").font = openpyxl.styles.Font(bold=True)
    ws6.cell(row=1, column=2, value="column_name").font = openpyxl.styles.Font(bold=True)
    ws6.cell(row=1, column=3, value="sensitive_type").font = openpyxl.styles.Font(bold=True)
    r = 2
    for row_data in final_rows:
        if row_data.get("sensitive_flag"):
            ws6.cell(row=r, column=1, value=row_data.get("table_name"))
            ws6.cell(row=r, column=2, value=row_data.get("column_name"))
            ws6.cell(row=r, column=3, value=row_data.get("sensitive_type"))
            r += 1

    outpath = os.path.join(OUTPUT_DIR, f"metadata_comparison_report_{ORACLE_SCHEMA}_{TIMESTAMP}.xlsx")
    wb.save(outpath)
    wb.close()
    print(f"[Output] 差异报告: {outpath} (6 sheets)")
    return outpath


def write_issue_summary(final_rows, stats):
    """输出问题汇总 markdown"""
    lines = []
    lines.append(f"# Oracle 元数据核对问题汇总")
    lines.append(f"Schema: {ORACLE_SCHEMA}")
    lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("## 统计概览")
    lines.append(f"- Oracle 表数: {stats['oracle_table_count']}")
    lines.append(f"- 字典表数: {stats['dictionary_table_count']}")
    lines.append(f"- 最终表数: {stats.get('final_table_count', 0)}")
    lines.append(f"- Oracle 字段数: {stats['oracle_column_count']}")
    lines.append(f"- 字典字段数: {stats['dictionary_column_count']}")
    lines.append(f"- 完全匹配: {stats['matched_column_count']}")
    lines.append(f"- 存在差异: {stats['mismatch_column_count']}")
    lines.append(f"- 仅Oracle存在: {stats['only_in_oracle_count']}")
    lines.append(f"- 仅字典存在: {stats['only_in_dictionary_count']}")
    lines.append(f"- 敏感字段: {stats['sensitive_field_count']}")
    if stats.get('corrupted_comment_count', 0) > 0:
        lines.append(f"- Oracle注释损坏: {stats['corrupted_comment_count']}")
    lines.append("")

    # Group issues by table
    issues_by_table = defaultdict(list)
    for row in final_rows:
        if row.get("diff_status") not in ("MATCHED",):
            issues_by_table[row.get("table_name")].append(row)

    if issues_by_table:
        lines.append("## 问题详情")
        for tname in sorted(issues_by_table.keys()):
            lines.append(f"\n### {tname}")
            for r in issues_by_table[tname]:
                lines.append(f"- `{r['column_name']}`: {r['diff_status']} - {r['recommendation']}")

    # Corrupted comments section
    corrupted = [r for r in final_rows if "COMMENT_CORRUPTED_IN_ORACLE" in str(r.get("diff_status", ""))]
    if corrupted:
        lines.append("\n## Oracle 注释损坏（字符集迁移问题）")
        lines.append("以下字段的注释在 Oracle 数据库中已损坏（全为问号），无法恢复原始中文。")
        lines.append("建议从人工数据字典中补充这些字段的注释。\n")
        corrupted_tables = defaultdict(list)
        for r in corrupted:
            corrupted_tables[r.get("table_name")].append(r.get("column_name"))
        for tname in sorted(corrupted_tables.keys()):
            cols = corrupted_tables[tname]
            lines.append(f"### {tname} ({len(cols)} 个字段)")
            lines.append(f"字段: {', '.join(cols)}")
            lines.append("")
    else:
        lines.append("## 无问题")
        lines.append("所有字段均匹配。")

    outpath = os.path.join(OUTPUT_DIR, f"metadata_issue_summary_{ORACLE_SCHEMA}_{TIMESTAMP}.md")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Output] 问题汇总: {outpath}")
    return outpath


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Oracle 元数据自动核对工具")
    print("=" * 60)

    # Step 1: Connect Oracle
    print("\n[Step 1] 连接 Oracle...")
    conn = connect_oracle()

    # Step 2: Fetch Oracle metadata
    print("\n[Step 2] 采集 Oracle 元数据...")
    oracle_tables = fetch_oracle_tables(conn)
    oracle_columns = fetch_oracle_columns(conn)
    oracle_pks = fetch_oracle_primary_keys(conn)
    oracle_fks = fetch_oracle_foreign_keys(conn)
    oracle_indexes = fetch_oracle_indexes(conn)
    conn.close()

    # Step 3: Parse dictionary files
    print("\n[Step 3] 解析人工数据字典...")
    dict_results = []
    for fpath in DICT_FILES:
        if not os.path.exists(fpath):
            print(f"[WARN] 字典文件不存在: {fpath}")
            continue
        try:
            fname = os.path.basename(fpath)
            if "数据仓库数据ACRM相关数据字典" in fname:
                result = parse_dict_file_1(fpath)
            elif "数据挖掘前期分析" in fname:
                result = parse_dict_file_2(fpath)
            elif "系统基础表字段级分析" in fname:
                result = parse_dict_file_3(fpath)
            else:
                continue
            dict_results.append(result)
        except Exception as e:
            print(f"[ERROR] 解析 {fpath} 失败: {e}")
            import traceback
            traceback.print_exc()

    if not dict_results:
        print("[ERROR] 没有成功解析任何数据字典文件")
        sys.exit(1)

    dict_tables, dict_columns = merge_dictionary(dict_results)

    # Step 4: Compare and reconcile
    print("\n[Step 4] 比对与调和...")
    final_rows, comparison_rows, stats = compare_and_reconcile(
        oracle_tables, oracle_columns, oracle_pks, oracle_fks, oracle_indexes,
        dict_tables, dict_columns
    )

    # Step 4b: 过滤注释损坏的表 (ZHS16GBK 迁移损坏)
    # 自动检测：任何字段注释全是问号的表视为注释永久损坏
    auto_corrupted = set()
    for r in final_rows:
        comment = r.get("final_column_comment")
        if comment and set(str(comment).strip()) == {"?"} and len(str(comment).strip()) >= 2:
            auto_corrupted.add(r.get("table_name"))
    # 合并手动指定的损坏表
    corrupted_tables = CORRUPTED_TABLES | auto_corrupted
    excluded = sum(1 for r in final_rows if r.get("table_name") in corrupted_tables)
    final_rows = [r for r in final_rows if r.get("table_name") not in corrupted_tables]
    comparison_rows = [r for r in comparison_rows if r.get("table_name") not in corrupted_tables]
    if excluded:
        print(f"\n[Filter] 已过滤 {excluded} 个注释损坏字段（{len(corrupted_tables)} 张表）")

    # Step 5: Output reports
    print("\n[Step 5] 生成报告...")
    write_final_metadata(final_rows)
    write_comparison_report(comparison_rows, stats, final_rows)
    write_issue_summary(final_rows, stats)

    print("\n" + "=" * 60)
    print("完成! 统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
