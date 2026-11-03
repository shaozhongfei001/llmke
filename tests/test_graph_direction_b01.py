"""B01 回归：关系去重键必须带方向，不许用 sorted() 把端点对一律压平。

外部评审 B01 的形态：`pair_key` 用 `tuple(sorted((src, dst)))` 做无序键，
于是 `甲 -担保-> 乙` 与 `乙 -担保-> 甲` 落成同一个键，只留**先到者**——
两条不同业务事实被压成一条，丢哪条取决于抽取顺序（不可复现、不可审计）。

判定口径（与 contracts/ontology/relations.v1.json 对齐，不在代码里猜）：
  1) 契约显式 symmetric=true（当前 相似/关联）→ 无序键，正反两向是同一事实，合并；
  2) 未登记谓词（如 担保）→ 有向键，方向**不可裁决**，两个方向都保留；
  3) 已登记但 domain==range / 通配 → 同样不可裁决，两个方向都保留；
  4) 已登记且 domain≠range → 键仍是有向的；反向由 resolve_direction 判为"伪反向边"，
     在 filter_reverse_duplicates 里被挡住（这一层不是靠压平键实现的）。

本文件直接对这些行为下断言，改坏任何一条都会红。
"""

import sys
from pathlib import Path

import pytest

GRAPH_DIR = (Path(__file__).resolve().parents[1]
             / "services" / "rag-alg" / "index_data_service" / "index_graph_service")
if str(GRAPH_DIR) not in sys.path:
    sys.path.insert(0, str(GRAPH_DIR))

import graph_types as gt  # noqa: E402


# ---------- 1. 有向谓词：反向不得合并 ----------

def test_reverse_directed_predicate_is_not_merged():
    """担保未登记 → 不可裁决 → 两个方向是两条事实，都不许丢。"""
    forward = gt.pair_key("担保", "甲", "乙")
    reverse = gt.pair_key("担保", "乙", "甲")
    assert forward != reverse, "B01 回归：有向谓词的正反两向不能落成同一个键"

    kept, skipped = gt.filter_reverse_duplicates([["甲", "担保", "乙"], ["乙", "担保", "甲"]])
    assert kept == [["甲", "担保", "乙"], ["乙", "担保", "甲"]]
    assert skipped == []

    # 反向判定也不能把对方当重复：谁担保谁是两条事实
    assert gt.is_reverse_duplicate("乙", "担保", "甲", {forward}) is False
    assert gt.is_reverse_duplicate("甲", "担保", "乙", {reverse}) is False
    # 不可裁决的理由要能说出来（不是"猜的"）
    assert gt.direction_determinable("担保") == (False, "predicate_unregistered")
    assert gt.resolve_direction("担保", "机构", "机构") == "unknown"


def test_domain_eq_range_predicate_keeps_both_directions():
    """已登记但 domain==range 的谓词同样不可裁决：双向都保留。"""
    rel = "办理流程中间"
    assert gt.direction_determinable(rel) == (False, "domain_eq_range")
    assert gt.pair_key(rel, "受理", "资料审核") != gt.pair_key(rel, "资料审核", "受理")

    kept, skipped = gt.filter_reverse_duplicates([["受理", rel, "资料审核"],
                                                  ["资料审核", rel, "受理"]])
    assert len(kept) == 2 and skipped == []


def test_unknown_predicate_keeps_both_directions():
    kept, skipped = gt.filter_reverse_duplicates([["甲", "随手写的谓词", "乙"],
                                                  ["乙", "随手写的谓词", "甲"]])
    assert len(kept) == 2 and skipped == []
    assert gt.pair_key("随手写的谓词", "甲", "乙") != gt.pair_key("随手写的谓词", "乙", "甲")


# ---------- 2. 显式对称谓词：仍然合并 ----------

def test_explicitly_symmetric_predicate_still_merged():
    """只有契约声明 symmetric=true 才允许无向键。"""
    for rel in ("相似", "关联"):
        assert rel in gt.SYMMETRIC_RELATIONS, f"{rel} 应由契约声明为对称"
        assert gt.relation_spec(rel)["symmetric"] is True
        assert gt.pair_key(rel, "甲", "乙") == gt.pair_key(rel, "乙", "甲")

    kept, skipped = gt.filter_reverse_duplicates([["甲", "相似", "乙"], ["乙", "相似", "甲"]])
    assert kept == [["甲", "相似", "乙"]]
    assert skipped == [["乙", "相似", "甲"]]


def test_symmetry_comes_from_contract_not_from_code():
    """对称性判据来自契约文件；未登记的谓词不会被当成对称。"""
    assert gt._REL_REASON == "contract", gt._REL_REASON
    assert "担保" not in gt.SYMMETRIC_RELATIONS
    assert gt.relation_spec("担保") is None
    assert gt.is_symmetric_relation("担保") is False


# ---------- 3. 不许 sorted() 压平：非对称谓词的键必须有方向 ----------

@pytest.mark.parametrize("rel", sorted(n for n, s in gt.RELATIONS.items()
                                       if not s.get("symmetric")) + ["担保", "随手写的谓词"])
def test_pair_key_is_directed_for_every_asymmetric_predicate(rel):
    a, b = gt.pair_key(rel, "甲", "乙"), gt.pair_key(rel, "乙", "甲")
    assert a != b, f"{rel} 被压平成无序键（sorted() 回归）"
    # 键的端点必须保序：第 2 段是 (src, dst)，不是排序后的元组
    assert a[1] == ("甲", "乙") and b[1] == ("乙", "甲")


# ---------- 4. 可裁决的非对称谓词：键有向，反向由本体判为伪反向边 ----------

def test_domain_range_decided_reverse_is_duplicate_but_key_stays_directed():
    rel = "利率基准"                     # product -> metric
    assert gt.direction_determinable(rel) == (True, "domain_range")
    assert gt.resolve_direction(rel, "产品", "指标") == "forward"
    assert gt.resolve_direction(rel, "指标", "产品") == "reverse"
    # 键本身仍带方向（不是靠压平键去重）
    assert gt.pair_key(rel, "智造贷", "1年期LPR") != gt.pair_key(rel, "1年期LPR", "智造贷")

    kept, skipped = gt.filter_reverse_duplicates([["智造贷", rel, "1年期LPR"],
                                                  ["1年期LPR", rel, "智造贷"]])
    assert kept == [["智造贷", rel, "1年期LPR"]]
    assert skipped == [["1年期LPR", rel, "智造贷"]]


# ---------- 5. 既有去重能力未被削弱 ----------

def test_exact_duplicate_still_deduplicated():
    kept, skipped = gt.filter_reverse_duplicates([["甲", "担保", "乙"], ["甲", "担保", "乙"]])
    assert kept == [["甲", "担保", "乙"]] and skipped == [["甲", "担保", "乙"]]


def test_existing_pairs_across_batches_are_respected():
    """跨批次：存量里已有 甲-担保->乙，再来 甲-担保->乙 算重复；乙-担保->甲 不算。"""
    existing = gt.build_pair_index([["甲", "担保", "乙"]])
    kept, skipped = gt.filter_reverse_duplicates([["甲", "担保", "乙"], ["乙", "担保", "甲"]],
                                                 existing_pairs=existing)
    assert kept == [["乙", "担保", "甲"]]
    assert skipped == [["甲", "担保", "乙"]]


def test_alias_predicates_share_one_key():
    """别名归一到契约名，避免同一事实因写法不同重复入账。"""
    assert gt.pair_key("适用产品", "客户甲", "智造贷") == gt.pair_key("授权产品", "客户甲", "智造贷")


def test_pair_key_scheme_is_declared():
    """审计用：键方案的版本要显式写出来，便于存量数据回放时对齐口径。"""
    assert gt.PAIR_KEY_SCHEME == "b01-ontology-directed-v1"
