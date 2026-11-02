#!/usr/bin/env python
"""Prometheus 文本的**契约断言**：给巡检/验收脚本共用，不依赖 prometheus_client。

为什么需要单独一层：之前的检查只问"某个字符串在不在"，于是
- `nan`/`inf` 能混过去（查询会变脏，但字符串检查看不出来）；
- TYPE 重复、标签不闭合也能过（Prometheus 抓取时才报错）；
- 配额只有 `used` 没有 `limit`，或者 `used > limit`，面板照样显示，没人发现。

这里做四类判定：
1. 语法：每行要么注释、要么 `name{labels} value`；标签必须闭合且无重复键；
2. 数值：必须是有限数（nan/inf 直接判违约——它们会污染 rate()/avg()）；
3. 元数据：同一指标名 `# TYPE` 只能出现一次；counter 名必须以 `_total` 结尾；
4. 业务：配额族必须成对出现（used/limit 同一组标签），且 `used <= limit`。

用法：
    python scripts/v2_metrics_contract.py --url http://127.0.0.1:18871/metrics
    python scripts/v2_metrics_contract.py --file /tmp/metrics.prom --require-quota
退出码：0 合规；1 违约；2 抓取失败。
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = "llmke.metrics-contract.v1"
NAME_RE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
SAMPLE_RE = re.compile(r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
                       r"(?P<labels>\{.*\})?\s+(?P<value>\S+)$")
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')

DEFAULT_REQUIRED = ("llmke_graph_scheduler_cycles_total", "llmke_graph_rebuild_pending")


def _parse_labels(raw: str, problems: List[str], line: str) -> Optional[Dict[str, str]]:
    text = raw.strip()
    if not (text.startswith("{") and text.endswith("}")):
        problems.append(f"标签未闭合：{line[:80]}")
        return None
    inner = text[1:-1].strip()
    labels: Dict[str, str] = {}
    if not inner:
        return labels
    for key, value in LABEL_RE.findall(inner):
        if key in labels:
            problems.append(f"标签键重复：{key}（{line[:60]}）")
        labels[key] = value
    # 去掉已识别部分后不应再有非空白残留，否则说明格式坏了
    leftover = LABEL_RE.sub("", inner).replace(",", "").strip()
    if leftover:
        problems.append(f"标签格式非法：{leftover[:40]}（{line[:60]}）")
    return labels


def parse(text: str) -> Dict[str, Any]:
    """解析成 {samples: {name: [ {labels, value, raw} ]}, types: {name: kind}, problems}。"""
    samples: Dict[str, List[Dict[str, Any]]] = {}
    types: Dict[str, str] = {}
    helps: Dict[str, int] = {}
    problems: List[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            parts = line.split(None, 3)
            if len(parts) >= 3 and parts[1] == "TYPE":
                name, kind = parts[2], (parts[3] if len(parts) > 3 else "")
                if name in types:
                    problems.append(f"TYPE 重复：{name}")
                types[name] = kind.split()[0] if kind else ""
            elif len(parts) >= 2 and parts[1] == "HELP":
                name = parts[2] if len(parts) > 2 else ""
                helps[name] = helps.get(name, 0) + 1
            continue
        match = SAMPLE_RE.match(line)
        if not match:
            problems.append(f"样本行格式错误：{line[:80]}")
            continue
        name = match.group("name")
        if not NAME_RE.match(name):
            problems.append(f"指标名非法：{name}")
        labels = _parse_labels(match.group("labels"), problems, line) if match.group("labels") else {}
        try:
            value = float(match.group("value"))
        except ValueError:
            problems.append(f"样本值非数字：{line[:60]}")
            continue
        if value != value or value in (float("inf"), float("-inf")):
            problems.append(f"出现 nan/inf：{line[:60]}")
        samples.setdefault(name, []).append({"labels": labels or {}, "value": value, "raw": line})
    for name, kind in types.items():
        if kind == "counter" and not name.endswith("_total"):
            problems.append(f"counter 名缺少 _total 后缀：{name}")
        # 只有 TYPE 没有样本是**合法**的（可选指标族当前为空），不要误判。
    for name in samples:
        if name not in types:
            problems.append(f"样本缺少 TYPE 声明：{name}")
    return {"samples": samples, "types": types, "helps": helps, "problems": problems}


def _num(value: float) -> str:
    """9.0 打成 "9"，错误信息才好读（也方便断言）。"""
    return str(int(value)) if float(value).is_integer() else str(value)


def _label_key(labels: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted(labels.items()))


def check_quota(samples: Dict[str, List[Dict[str, Any]]],
                problems: List[str]) -> Dict[str, Any]:
    """配额族的两条硬约束：used/limit 必须成对；used 不得超过 limit。"""
    used_series = samples.get("llmke_graph_quota_used") or []
    limit_series = samples.get("llmke_graph_quota_limit") or []
    limits = {_label_key(item["labels"]): item["value"] for item in limit_series}
    tenants = []
    for item in used_series:
        key = _label_key(item["labels"])
        tenant = item["labels"].get("tenant")
        if not tenant:
            problems.append("配额指标缺少 tenant 标签")
            continue
        tenants.append(tenant)
        if key not in limits:
            problems.append(f"配额 used 没有对应 limit（tenant={tenant}）")
            continue
        if item["value"] > limits[key]:
            problems.append(f"配额 used({_num(item['value'])}) > limit({_num(limits[key])})"
                            f"（tenant={tenant}）")
    return {"tenants": sorted(tenants), "used_series": len(used_series),
            "limit_series": len(limit_series)}


def validate(text: str, *, required=DEFAULT_REQUIRED,
             require_quota: bool = False) -> Dict[str, Any]:
    parsed = parse(text)
    problems = list(parsed["problems"])
    missing = [name for name in required if name not in parsed["samples"]]
    if missing:
        problems.append(f"缺少必需指标：{missing}")
    quota = check_quota(parsed["samples"], problems)
    if require_quota and not quota["used_series"]:
        problems.append("要求存在配额指标（llmke_graph_quota_used），实际没有")
    return {"schema": SCHEMA, "problems": problems,
            "series": len(parsed["samples"]), "types": len(parsed["types"]),
            "quota": quota, "ok": not problems}


def fetch(url: str, timeout: float = 5.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None, help="例如 http://127.0.0.1:18871/metrics")
    ap.add_argument("--file", default=None, help="直接读一份文本（离线校验）")
    ap.add_argument("--require-quota", action="store_true")
    ap.add_argument("--required", nargs="*", default=list(DEFAULT_REQUIRED))
    ap.add_argument("--bearer", default=None, help="/metrics 需要鉴权时的 token")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.file:
        text = open(args.file, encoding="utf-8").read()
    elif args.url:
        request = urllib.request.Request(args.url)
        if args.bearer:
            request.add_header("Authorization", f"Bearer {args.bearer}")
        try:
            with urllib.request.urlopen(request, timeout=8) as resp:
                text = resp.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"schema": SCHEMA, "ok": False,
                              "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
            return 2
    else:
        raise SystemExit("需要 --url 或 --file")

    report = validate(text, required=args.required, require_quota=args.require_quota)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("ok", "series", "quota", "problems")},
                     ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
