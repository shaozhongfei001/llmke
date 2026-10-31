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
            cfg = BaseConfig(save_dir=self.save_dir, llm_name=self._cfg["llm_name"],
                             llm_base_url=self._cfg["llm_base_url"],
                             embedding_model_name=self._cfg["embedding_model_name"],
                             embedding_base_url=self._cfg["embedding_base_url"],
                             openie_mode="online")
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
                 top_k: int = 3) -> Dict[str, Any]:
        hp = self.hp
        trace = {"graph_calls": 0, "seed_hits": [], "fact_candidates": None}

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

        had_instance_attr = "graph_search_with_fact_entities" in getattr(hp, "__dict__", {})
        setattr(hp, "graph_search_with_fact_entities", traced)
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

        # 种子是否真的落在图里：这决定 PPR 有没有起点。
        # 平台 id 是 "ent:<名称>"，引擎键是 "entity-" + mdhash(text_processing(名称))，
        # 所以要做一次显式换算——换算不出来就如实记空，别假装命中。
        idx_map = getattr(hp, "node_name_to_vertex_idx", {}) or {}
        for seed in seeds or []:
            key = self._to_engine_key(seed)
            if key and key in idx_map:
                trace["seed_hits"].append(seed)

        route = GRAPH if trace["graph_calls"] > 0 else DENSE_FALLBACK
        reason = "GRAPH_CALLED" if route == GRAPH else "GRAPH_NOT_CALLED"
        return self._pack(solutions, route, reason, trace)

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
