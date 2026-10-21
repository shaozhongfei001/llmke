#!/usr/bin/env python3
"""Shared PL/SQL text utilities for gates (comment stripping, segmentation)."""
from __future__ import annotations

import re

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"--[^\n]*")


def strip_comments(text: str) -> str:
    """Remove PL/SQL comments while preserving line numbers."""
    if not text:
        return ""
    text = _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    text = _LINE_COMMENT.sub("", text)
    return text


def line_of(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def find_statement_end(text: str, start_pos: int) -> int:
    """Return offset just past the terminating ';' (or end of text)."""
    semi = text.find(";", start_pos)
    return semi + 1 if semi != -1 else len(text)


def segment_lines(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[max(0, start_line - 1) : end_line])


def split_top_level(s: str, sep: str = ",") -> list[str]:
    """Split on separator at parenthesis depth 0 (single quotes honored)."""
    out, buf, depth, in_q = [], [], 0, False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_q:
            buf.append(ch)
            if ch == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    buf.append("'")
                    i += 1
                else:
                    in_q = False
            i += 1
            continue
        if ch == "'":
            in_q = True
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "IS", "IN", "LIKE",
    "BETWEEN", "CASE", "WHEN", "THEN", "ELSE", "END", "AS", "ON", "JOIN",
    "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "CROSS", "GROUP", "BY", "ORDER",
    "HAVING", "UNION", "ALL", "DISTINCT", "INSERT", "INTO", "VALUES", "UPDATE",
    "SET", "DELETE", "MERGE", "USING", "MATCHED", "CREATE", "TABLE", "WITH",
    "OVER", "PARTITION", "ASC", "DESC", "EXISTS", "ROWNUM", "DUAL", "SYSDATE",
}

SQL_FUNCTIONS = {
    "NVL", "NVL2", "COALESCE", "TO_CHAR", "TO_DATE", "TO_NUMBER", "CAST",
    "SUBSTR", "INSTR", "TRIM", "LTRIM", "RTRIM", "UPPER", "LOWER", "LENGTH",
    "ROUND", "TRUNC", "MOD", "ABS", "SIGN", "SUM", "COUNT", "AVG", "MAX",
    "MIN", "DECODE", "REPLACE", "REGEXP_REPLACE", "REGEXP_SUBSTR",
    "ADD_MONTHS", "LAST_DAY", "MONTHS_BETWEEN", "GREATEST", "LEAST",
    "NULLIF", "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD", "SYSDATE",
    "CONCAT", "INITCAP", "TRANSLATE", "LPAD", "RPAD", "FLOOR", "CEIL",
}

_IDENT = re.compile(r"\b([A-Za-z][A-Za-z0-9_$#]*)\b")


def extract_columns(expr: str) -> list[str]:
    """Heuristic column identifiers in an expression (keywords/functions removed)."""
    cols = []
    for tok in _IDENT.findall(expr or ""):
        up = tok.upper()
        if up in SQL_KEYWORDS or up in SQL_FUNCTIONS:
            continue
        if up not in cols:
            cols.append(up)
    return cols


def classify_expression(expr: str) -> str:
    e = (expr or "").strip()
    up = e.upper()
    if not e:
        return "UNKNOWN"
    if re.search(r"SUM\s*\([^)]*\)\s*/", up) or re.search(
        r"/\s*(?:NULLIF\s*\()?\s*SUM\s*\(", up
    ):
        return "RATIO"
    if re.search(r"\b(SUM|COUNT|AVG|MIN|MAX)\s*\(", up):
        return "AGGREGATION"
    if re.search(r"\bOVER\s*\(", up):
        return "WINDOW"
    if re.search(r"\b(CASE|DECODE\s*\()", up):
        return "CASE_MAPPING"
    if re.search(r"\b(NVL|NVL2|COALESCE)\s*\(", up):
        return "NULL_DEFAULT"
    if re.search(r"\b(TO_CHAR|TO_DATE|TO_NUMBER|CAST)\s*\(", up):
        return "TYPE_CAST"
    if re.search(r"\b(TRUNC|ADD_MONTHS|LAST_DAY|MONTHS_BETWEEN)\s*\(", up):
        return "DATE_TRANSFORM"
    if "||" in e:
        return "CONCAT"
    if re.fullmatch(r"'[^']*'|-?\d+(\.\d+)?", e):
        return "CONSTANT"
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_$#]*(\.[A-Za-z][A-Za-z0-9_$#]*)?", e):
        return "DIRECT_COPY"
    if re.search(r"[+\-*/]", e):
        return "ARITHMETIC"
    return "UNKNOWN"
