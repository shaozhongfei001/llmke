"""HippoRAG 适配器：只做"把引擎包成平台可调的形状"，不改引擎算法。

关键点：**`executed_route` 来自真实调用痕迹，不是猜的。**
- 我们在调用期间临时包住 `graph_search_with_fact_entities`（引擎的图检索入口），
  记录它是否被调用、种子实体解析到几个、事实候选多少；
- 调用结束恢复原方法（不长期污染引擎实例）；
- 没被调用 → `executed_route=DENSE_FALLBACK`。这样"检索有结果"就不会被冒充成"图执行过"
  （设计 §6.5 的硬要求）。

`hp` 可以注入，测试用假对象即可验包装逻辑，不必加载模型。
"""

import glob
import json
import os
from typing import Any, Dict, List, Optional, Sequence

from .assertions import GRAPH, DENSE_FALLBACK

SCHEMA = "llmke.graph-engine.hipporag.v1"


class HippoRAGEngine:
    def __init__(self, hp: Any = None, *, save_dir: Optional[str] = None,
                 llm_name: str = "qwen2.5-7b-instruct", llm_base_url: Optional[str] = None,
                 embedding_model_name: str = "text-embedding-bge-m3",
                 embedding_base_url: Optional[str] = None):
        self._hp = hp
        self.save_dir = save_dir or (hp and getattr(hp.global_config, "save_dir", None))
        self._cfg = {"llm_name": llm_name, "llm_base_url": llm_base_url,
                     "embedding_model_name": embedding_model_name,
                     "embedding_base_url": embedding_base_url}

    # ---------- 构造 ----------
    @property
    def hp(self):
        if self._hp is None:
            from hipporag import HippoRAG
            from hipporag.utils.config_utils import BaseConfig

            os.environ.setdefault("OPENAI_API_KEY", "sk-local")
            extra = {}
            # 抽取是 LLM 采样的：同一语料两次全量构建会得到不同三元组，进而让"检索是否一致"
            # 无法归因（实测基线 top1 只有 0.667）。这里允许用环境变量显式固定温度/种子，
            # **不默认写死**——是否可复现取决于服务端实现，声称"设了 0 就一定确定"是骗人。
            if os.environ.get("LLMKE_LLM_TEMPERATURE"):
                extra["temperature"] = float(os.environ["LLMKE_LLM_TEMPERATURE"])
            if os.environ.get("LLMKE_LLM_SEED"):
                extra["seed"] = int(os.environ["LLMKE_LLM_SEED"])
            cfg = BaseConfig(save_dir=self.save_dir, llm_name=self._cfg["llm_name"],
                             llm_base_url=self._cfg["llm_base_url"],
                             embedding_model_name=self._cfg["embedding_model_name"],
                             embedding_base_url=self._cfg["embedding_base_url"],
                             openie_mode="online", **extra)
            self._hp = HippoRAG(global_config=cfg)
            self.save_dir = self._hp.global_config.save_dir
        return self._hp

    # ---------- 建索引 ----------
    def build(self, texts: Sequence[str]) -> Dict[str, Any]:
        hp = self.hp
        hp.index(list(texts))
        rows = hp.chunk_embedding_store.get_all_id_to_rows()
        return {"schema": SCHEMA, "chunks": len(rows),
                "chunk_ids": sorted(rows)[:3], "save_dir": self.save_dir}

    # ---------- 增量：删除 + 只对新增块抽取 ----------
    def all_texts(self) -> List[str]:
        """引擎里现存的所有块文本。增量差异以**文本集合**为准（块 id 就是文本哈希）。"""
        hp = self.hp
        store = getattr(hp, "chunk_embedding_store", None)
        if store is None or not hasattr(store, "get_all_texts"):
            return []
        return list(store.get_all_texts())

    def apply_delta(self, texts: Sequence[str]) -> Dict[str, Any]:
        """把快照调整成"恰好这些文本"：删掉多出来的，只对新增块跑抽取。

        为什么按文本差集而不是按 file_id：块 id 是文本哈希，撤权/改名/内容微调在引擎眼里
        都是"这段文本没了、那段文本来了"。按 file_id 做需要额外的映射表，多一层就多一处会错。

        真实收益在 `hp.index(to_add)`：它会 `load_existing_openie()` 复用已有抽取结果，
        只对 `to_add` 调 LLM。**图构建仍然是全量**（add_fact_edges 遍历所有块），
        所以这是"增量抽取 + 全量重建图"，不是"增量图更新"——别把两者说成一回事。
        """
        hp = self.hp
        wanted = list(dict.fromkeys(str(t) for t in texts))     # 去重保序
        existing = set(self.all_texts())
        to_delete = sorted(existing - set(wanted))
        to_add = [t for t in wanted if t not in existing]

        if to_delete:
            hp.delete(to_delete)
        if to_add:
            hp.index(to_add)

        remaining = len(hp.chunk_embedding_store.get_all_id_to_rows())
        return {"schema": SCHEMA, "deleted": len(to_delete), "added": len(to_add),
                "reused": len(wanted) - len(to_add), "duplicates": len(texts) - len(wanted),
                "remaining": remaining, "expected": len(wanted),
                "consistent": remaining == len(wanted)}

    # ---------- 抽取结果 ----------
    def openie_docs(self) -> List[Dict[str, Any]]:
        """读引擎落盘的 openie 结果（这是我们归一化的输入，不是权威事实）。"""
        pattern = os.path.join(self.save_dir or "", "openie_results_ner_*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            return []
        data = json.load(open(files[-1], encoding="utf-8"))
        return list(data.get("docs") or [])

    # ---------- 检索（带真实 trace） ----------
    def retrieve(self, query: str, seeds: Optional[Sequence[str]] = None,
                 top_k: int = 3, use_graph: bool = True) -> Dict[str, Any]:
        hp = self.hp
        trace = {"graph_calls": 0, "seed_hits": [], "fact_candidates": None,
                 "rerank_fallback": False, "graph_enabled": bool(use_graph)}

        # 禁用图对照（D6）：上游 `retrieve` 的图/稠密分支**只由 `len(top_k_facts)==0` 决定**
        # （HippoRAG.py:411-423），不存在"跑图但不计数"的中间态。所以"禁用图"的正确做法是
        # "不给事实"，让上游自己走 dense_passage_retrieval；同时把原因写成人为禁用，
        # 既不冒充 GRAPH，也不把它算成引擎故障。
        if not use_graph:
            original_facts = getattr(hp, "rerank_facts", None)
            disabled = {"candidates": 0}
            if original_facts is not None:
                def _dense_only(q, scores, _orig=original_facts):
                    out = _orig(q, scores)
                    before = (out[2] or {}).get("facts_before_rerank") or []
                    disabled["candidates"] = len(before)
                    return [], [], {"facts_before_rerank": before,
                                    "facts_after_rerank": [],
                                    "graph_disabled": "GRAPH_DISABLED"}
                setattr(hp, "rerank_facts", _dense_only)
            try:
                solutions = hp.retrieve([query], num_to_retrieve=top_k)
            finally:
                if original_facts is not None:
                    setattr(hp, "rerank_facts", original_facts)
            trace["fact_candidates"] = disabled["candidates"]
            # 人为清空事实 → 上游必然走稠密；这里如实写 0，别让人误读成"重排器没选出事实"。
            trace["facts_after_rerank"] = 0
            trace["graph_disabled"] = "GRAPH_DISABLED"
            self._fill_seed_hits(hp, seeds, trace)
            return self._pack(solutions, DENSE_FALLBACK, "GRAPH_DISABLED", trace)

        original = getattr(hp, "graph_search_with_fact_entities", None)
        if original is None:
            solutions = hp.retrieve([query], num_to_retrieve=top_k)
            return self._pack(solutions, DENSE_FALLBACK, "NO_GRAPH_SEARCH_METHOD", trace)

        def traced(*args, **kwargs):
            trace["graph_calls"] += 1
            try:
                return original(*args, **kwargs)
            except TypeError:
                raise

        # 上游 rerank 期望 DSPy 标记格式（[[ ## fact_after_filter ## ]]）。
        # qwen 常直接回 JSON，解析为空后 hp.retrieve 会静默走 dense，图检索一次都没跑。
        # 这里在“有候选、过滤后为空”时退回按向量分取前 link_top_k，并记 rerank_fallback；
        # 只在过滤【异常为空】时兜底，正常过滤出结果时完全不动上游行为。
        original_rerank = getattr(hp, "rerank_facts", None)
        rerank_state = {"candidates": 0}

        def rerank_guard(query, scores, _orig=original_rerank):
            idx, facts, log = _orig(query, scores)
            cands = list(log.get("facts_before_rerank") or [])
            rerank_state["candidates"] = len(cands)
            rerank_state["after"] = len(list(facts or []))
            if facts or not cands:
                return idx, facts, log
            try:
                import numpy as np

                k = int(getattr(hp.global_config, "linking_top_k", len(cands)) or len(cands))
                order = (np.argsort(scores)[-k:][::-1] if len(scores) > k
                         else np.argsort(scores)[::-1]).tolist()
            except Exception:  # noqa: BLE001 - 兜底路径不因 numpy/配置形状失败
                k = min(len(cands), 5)
                order = list(range(k))
            trace["rerank_fallback"] = True
            return order, cands[:min(k, len(cands))], log

        # 上游 `get_top_k_weights` 结尾断言"被选中的短语权重都非零"。
        # 实测小语料/CJK 短语会出现 number_of_occurs=0 的短语，被选中但权重为 0，
        # 断言直接抛 AssertionError，整个查询 500。这里只跳过这条**自检**：
        # 仍按上游规则截断 linking_score_map，PPR 照常执行；跳过事实记入 trace，
        # 不允许静默当成正常路径。
        original_weights = getattr(hp, "get_top_k_weights", None)
        weights_state = {"skipped": False}

        def weights_guard(link_top_k, weights, map_, _orig=original_weights):
            try:
                return _orig(link_top_k, weights, map_)
            except AssertionError:
                weights_state["skipped"] = True
                ordered = dict(sorted(map_.items(), key=lambda kv: kv[1], reverse=True)[:link_top_k])
                return weights, ordered

        had_weights_attr = "get_top_k_weights" in getattr(hp, "__dict__", {})
        had_instance_attr = "graph_search_with_fact_entities" in getattr(hp, "__dict__", {})
        had_rerank_attr = "rerank_facts" in getattr(hp, "__dict__", {})
        setattr(hp, "graph_search_with_fact_entities", traced)
        if original_rerank is not None:
            setattr(hp, "rerank_facts", rerank_guard)
        if original_weights is not None:
            setattr(hp, "get_top_k_weights", weights_guard)
        try:
            solutions = hp.retrieve([query], num_to_retrieve=top_k)
        finally:
            # 原来是类方法就删掉实例属性；原来就有实例属性则还原。避免长期污染引擎实例
            if had_instance_attr:
                setattr(hp, "graph_search_with_fact_entities", original)
            else:
                try:
                    delattr(hp, "graph_search_with_fact_entities")
                except AttributeError:
                    pass
            if original_rerank is not None:
                if had_rerank_attr:
                    setattr(hp, "rerank_facts", original_rerank)
                else:
                    try:
                        delattr(hp, "rerank_facts")
                    except AttributeError:
                        pass
            if original_weights is not None:
                if had_weights_attr:
                    setattr(hp, "get_top_k_weights", original_weights)
                else:
                    try:
                        delattr(hp, "get_top_k_weights")
                    except AttributeError:
                        pass
        trace["fact_candidates"] = rerank_state["candidates"]
        # 重排器自己选出几条事实：图分支的触发条件就是"这里非 0"（上游 HippoRAG.py:411-423）。
        # 只有它非 0 且 rerank_fallback=false，才算"图真的靠重排结果跑起来"。
        trace["facts_after_rerank"] = rerank_state.get("after")
        trace["weights_assert_skipped"] = weights_state["skipped"]

        self._fill_seed_hits(hp, seeds, trace)

        route = GRAPH if trace["graph_calls"] > 0 else DENSE_FALLBACK
        reason = "GRAPH_CALLED" if route == GRAPH else "GRAPH_NOT_CALLED"
        return self._pack(solutions, route, reason, trace)

    @classmethod
    def _fill_seed_hits(cls, hp: Any, seeds: Optional[Sequence[str]],
                        trace: Dict[str, Any]) -> None:
        """种子是否真的落在图里：这决定 PPR 有没有起点。

        平台 id 是 "ent:<名称>"，引擎键是 "entity-" + mdhash(text_processing(名称))，
        所以要做一次显式换算——换算不出来就如实记空，别假装命中。

        已知陷阱（实测）：上游 `text_processing` 会把中文清成空串，于是**任意**中文种子的
        换算键都是 `entity-d41d8cd98f00b204e9800998ecf8427e`（md5("")）。命中它并不代表
        "种子在图里"，只代表"中文被抹平了"。这种命中单独记进 `seed_hits_degenerate`，
        不计入 `seed_hits`，避免把空实体当种子证据。
        """
        idx_map = getattr(hp, "node_name_to_vertex_idx", {}) or {}
        empty_key = cls._to_engine_key("") or ""
        for seed in seeds or []:
            key = cls._to_engine_key(seed)
            if not key or key not in idx_map:
                continue
            if empty_key and key == empty_key:
                trace.setdefault("seed_hits_degenerate", []).append(seed)
                continue
            trace["seed_hits"].append(seed)

    @staticmethod
    def _to_engine_key(seed: str) -> Optional[str]:
        s = str(seed)
        if s.startswith("entity-"):
            return s
        name = s[4:] if s.startswith("ent:") else s
        try:
            import sys

            misc = sys.modules.get("hipporag.utils.misc_utils")
            if misc is None:
                return None
            processed = misc.text_processing(name)
            return misc.compute_mdhash_id(processed, prefix="entity-")
        except Exception:  # noqa: BLE001 - 换算失败就是没命中，不猜
            return None

    @staticmethod
    def _pack(solutions, route, reason, trace):
        hits = []
        for sol in solutions or []:
            for doc in getattr(sol, "docs", None) or []:
                hits.append(doc)
        return {"executed_route": route, "reason": reason, "trace": trace,
                "docs": hits, "hit_count": len(hits)}


class EngineRetriever:
    """把引擎包成 `pipeline.retrieve` 需要的 retriever（dense/graph 两个入口）。

    两者都调同一个引擎，但**图入口会走真实图检索**；返回的 `executed_route` 由引擎侧 trace 决定。
    这样 pipeline 的 planned 路线与 engine 的 executed 路线可以对照，不一致时能看见。
    """

    def __init__(self, engine: HippoRAGEngine, source_lookup=None):
        self.engine = engine
        self.source_lookup = source_lookup or (lambda doc: [])
        self.calls = []
        self.last_executed_route = None   # 供 pipeline 对照计划与执行

    def _to_hits(self, out):
        return [{"text": d, "sources": self.source_lookup(d)} for d in out["docs"]]

    def dense(self, query, top_k):
        out = self.engine.retrieve(query, seeds=None, top_k=top_k)
        self.last_executed_route = out["executed_route"]
        self.calls.append({"path": "dense", "executed_route": out["executed_route"],
                           "trace": out["trace"]})
        return self._to_hits(out)

    def graph(self, query, seeds, top_k):
        out = self.engine.retrieve(query, seeds=seeds, top_k=top_k)
        self.last_executed_route = out["executed_route"]
        self.calls.append({"path": "graph", "executed_route": out["executed_route"],
                           "trace": out["trace"]})
        return self._to_hits(out)
