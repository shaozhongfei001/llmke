"""R13 图谱类型体系 / 实体过滤 / canonical 归一。

定位：不改原抽取 Prompt 与 LLM 协议，只在"抽取结果落库之前"加一层确定性的规范化，
解决实测暴露的三类问题：
  1. 纯数字、结构性词（下表/table/天数）被当成实体入图；
  2. LLM 给的类型不在业务类型表里，或直接落到"其他"；
  3. 同一实体的长短名（华东 / 华东精密制造有限公司）被拆成两个节点。

设计约束（与用户要求对齐）：
  - 类型体系带版本号 SCHEMA_VERSION，写入响应与审计，便于后续演进与回溯；
  - 未能判定类型的实体不静默丢弃，标记为 unclassified 并在响应里返回清单（可人工复核）；
  - 归一只做**确定可解释**的规则（别名表 + 全称包含关系），不做不可复现的猜测。
"""
import json
import os
import re

SCHEMA_VERSION = "v1"

# 业务类型表（v1）：与知识库的 graphPrompt/entity_types 同口径，作为"合法类型"白名单
ALLOWED_TYPES = [
    "机构", "客户", "产品", "金额", "期限", "指标", "日期",
    "业务动作", "单证", "条款", "评级", "地点", "其他",
]

# 规则推断：LLM 没给出合法类型时，按名称形态兜底
RULES = [
    ("金额", re.compile(r"(人民币)?\s*[\d,.]+\s*(万元|亿元|元)")),
    ("日期", re.compile(r"^\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?日?$")),
    ("期限", re.compile(r"^[一二三四五六七八九十百\d]+\s*(个工作日|个工作日|个月|年|天|日)$")),
    ("评级", re.compile(r"^(AAA|AA|A|BBB|BB|B|CCC|CC|C)$")),
    ("指标", re.compile(r"(率|占比|额度|余额|存款|用电量|同比|环比|天数|金额)$")),
    ("单证", re.compile(r"^[A-Z]{1,4}-[A-Z]{2,}-\d+")),
    ("机构", re.compile(r"(公司|集团|银行|中心|工厂|厂|企业|机构|研究院|大学)$")),
    ("地点", re.compile(r"(省|市|区|县|镇|街道)$")),
    ("条款", re.compile(r"(等额本息|等额本金|按月付息|按季付息|到期还本|分期还本|先息后本)")),
    ("评级", re.compile(r"^(正常|关注|次级|可疑|损失)$")),
    ("产品", re.compile(r"(贷|票据|贴现|保理|理财|存款|险)$")),
]

# 明确不是实体的结构性词 / 表头词 / 通用词
STOPWORDS = {
    "下表", "上表", "表格", "表头", "table", "document", "docx", "xlsx", "pptx", "pdf",
    "文本", "内容", "数据", "天数", "业务日", "序号", "备注", "合计", "小计", "单位",
    "正常", "无", "其他", "如下", "上述", "以上", "以下", "说明",
}

RULE_DATE = re.compile(r"^\d{4}[-/年]\d{1,2}([-/月]\d{1,2})?日?$")
RULE_AMOUNT = re.compile(r"(人民币)?\s*[\d,.]+\s*(万元|亿元|元)")
DOC_TITLE = re.compile(r"^(docx|xlsx|pptx|pdf|word|excel)[\s_\-.]*", re.I)
CJK_OR_ALNUM = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9]")
PURE_NUMBER = re.compile(r"^[\d,.\-%]+$")
COMPANY_SUFFIX = re.compile(r"(股份有限公司|有限责任公司|有限公司|集团有限公司|集团|公司|银行|中心)$")

_ALIAS_CACHE = None


def _alias_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "alias_map.json")


def load_alias_map():
    """别名表（可选）：{"别名": "标准名"}，缺失时返回空表，不影响主链。"""
    global _ALIAS_CACHE
    if _ALIAS_CACHE is not None:
        return _ALIAS_CACHE
    path = _alias_file()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                _ALIAS_CACHE = {str(k).strip(): str(v).strip() for k, v in json.load(f).items()}
        except Exception:
            _ALIAS_CACHE = {}
    else:
        _ALIAS_CACHE = {}
    return _ALIAS_CACHE


def clean_name(name):
    if name is None:
        return ""
    s = str(name).strip()
    s = s.strip("\"'“”‘’《》<>()（）[]【】")
    s = re.sub(r"\s+", "", s)
    return s


def is_valid_entity(name):
    """过滤纯数字、纯符号、结构词、过短/过长。返回 (bool, reason)。"""
    s = clean_name(name)
    if not s:
        return False, "empty"
    if s.lower() in STOPWORDS:
        return False, "stopword"
    # 日期要保留（是业务实体），不能因为形如数字带连字符被当成纯数字过滤
    if RULE_DATE.match(s) or RULE_AMOUNT.match(s):
        return True, ""
    if PURE_NUMBER.match(s):
        return False, "pure_number"
    # 文档标题/文件名不该成为实体（如 "DOCX with table"、"xxx.xlsx"）
    if DOC_TITLE.match(s):
        return False, "doc_title"
    if not CJK_OR_ALNUM.search(s):
        return False, "no_alnum"
    if len(s) < 2:
        return False, "too_short"
    if len(s) > 30:
        return False, "too_long"
    return True, ""


def infer_type(name, llm_type):
    """优先采用 LLM 给出的合法类型；否则按规则推断；都不中则 unclassified。"""
    t = clean_name(llm_type)
    if t in ALLOWED_TYPES and t not in ("其他",):
        return t, "llm"
    for type_name, pattern in RULES:
        if pattern.search(clean_name(name)):
            return type_name, "rule"
    return "unclassified", "none"


def canonical_of(name, all_names, alias_map=None):
    """
    canonical 归一（确定性规则）：
      1) 命中别名表 -> 用标准名；
      2) 名称是另一实体名的严格前缀，且后者带公司/机构后缀 -> 归到后者（长名优先）。
    其余保持自身。
    """
    s = clean_name(name)
    alias_map = alias_map if alias_map is not None else load_alias_map()
    if s in alias_map:
        return alias_map[s]
    candidates = []
    for other in all_names:
        o = clean_name(other)
        if o == s or not COMPANY_SUFFIX.search(o):
            continue
        if o.startswith(s) and len(o) > len(s):
            candidates.append(o)
    if candidates:
        # 取最短的合法全称，避免一路并到过长的复合名
        return sorted(candidates, key=len)[0]
    return s


def normalize_graph_data(triples_data_list, entity_source_dict, triples_source_dict):
    """
    返回 (triples, entities, triples_source, report)。
    report 里带 schema_version、被过滤实体及原因、合并映射、未分类实体。
    """
    alias_map = load_alias_map()
    raw_names = [n for n, v in entity_source_dict.items() if v.get("entity_type") == "1"]

    kept, filtered, merged, unclassified = {}, [], {}, []
    name_map = {}

    for name in raw_names:
        ok, reason = is_valid_entity(name)
        if not ok:
            filtered.append({"name": clean_name(name), "reason": reason})
            continue
        canon = canonical_of(name, raw_names, alias_map)
        name_map[name] = canon
        if clean_name(name) != canon:
            merged[clean_name(name)] = canon

    # 合并实体属性（title / file_id / e_type 取并集），类型冲突时保留首个已判定类型
    for name, canon in name_map.items():
        src = entity_source_dict[name]
        if canon not in kept:
            # 保留原字典的**全部**字段（chunk_pk_list / e_type / title / file_id ...），
            # 只对列表型字段做并集，避免下游因缺字段 KeyError。
            bucket = {k: (list(v) if isinstance(v, list) else v) for k, v in src.items()}
            bucket["entity_type"] = "1"
            kept[canon] = bucket
        else:
            bucket = kept[canon]
            for key, val in src.items():
                if key == "entity_type":
                    continue
                if isinstance(val, list):
                    bucket.setdefault(key, [])
                    for v in val:
                        if v not in bucket[key]:
                            bucket[key].append(v)
                else:
                    bucket.setdefault(key, val)
        # 类型推断
        llm_type = next((t for t in bucket["e_type"] if t), "")
        typ, source = infer_type(canon, llm_type)
        bucket["e_type"] = [typ]
        if typ == "unclassified":
            unclassified.append(canon)

    # 重写三元组
    new_triples = []
    dropped_triples = 0
    for td in triples_data_list:
        try:
            src, rel, dst = clean_name(td[0]), clean_name(td[1]), clean_name(td[2])
        except Exception:
            dropped_triples += 1
            continue
        if src not in name_map or dst not in name_map:
            dropped_triples += 1
            continue
        src, dst = name_map[src], name_map[dst]
        if src == dst:
            dropped_triples += 1
            continue
        new_triples.append((src, rel, dst))

    # triples_source 的 key 是 "src,rel,dst"
    new_triples_source = {}
    for key, val in (triples_source_dict or {}).items():
        parts = str(key).split(",")
        if len(parts) != 3:
            continue
        s0, r0, d0 = clean_name(parts[0]), parts[1], clean_name(parts[2])
        if s0 not in name_map or d0 not in name_map:
            continue
        new_key = f"{name_map[s0]},{r0},{name_map[d0]}"
        new_triples_source[new_key] = val

    report = {
        "schema_version": SCHEMA_VERSION,
        "kept_entities": len(kept),
        "filtered": filtered,
        "merged": merged,
        "unclassified": unclassified,
        "dropped_triples": dropped_triples,
    }
    return new_triples, kept, new_triples_source, report
