# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# # @Time    : 2024/5/31 15:14
# # @Author  : yuxj
# # @File    : kb_cache.py
# import sys
# import os
#
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))
#
# from langchain.embeddings.base import Embeddings
# import threading
# from contextlib import contextmanager
# from collections import OrderedDict
# from typing import List, Any, Union, Tuple
#
# from utils import get_config
#
# server_config = get_config()
# embedding_model = get_config()["embedding_model"]
#
#
# class ThreadSafeObject:
#     def __init__(self, key: Union[str, Tuple], obj: Any = None, pool: "CachePool" = None):
#         self._obj = obj
#         self._key = key
#         self._pool = pool
#         self._lock = threading.RLock()
#         self._loaded = threading.Event()
#
#     def __repr__(self) -> str:
#         cls = type(self).__name__
#         return f"<{cls}: key: {self.key}, obj: {self._obj}>"
#
#     @property
#     def key(self):
#         return self._key
#
#     @contextmanager
#     def acquire(self, owner: str = "", msg: str = ""):
#         owner = owner or f"thread {threading.get_native_id()}"
#         try:
#             self._lock.acquire()
#             if self._pool is not None:
#                 self._pool._cache.move_to_end(self.key)
#             yield self._obj
#         finally:
#             self._lock.release()
#
#     def start_loading(self):
#         self._loaded.clear()
#
#     def finish_loading(self):
#         self._loaded.set()
#
#     def wait_for_loading(self):
#         self._loaded.wait()
#
#     @property
#     def obj(self):
#         return self._obj
#
#     @obj.setter
#     def obj(self, val: Any):
#         self._obj = val
#
#
# class CachePool:
#     def __init__(self, cache_num: int = 10):
#         self._cache_num = cache_num
#         self._cache = OrderedDict()
#         self.atomic = threading.RLock()
#
#     def keys(self) -> List[str]:
#         return list(self._cache.keys())
#
#     def _check_count(self):
#         if isinstance(self._cache_num, int) and self._cache_num > 0:
#             while len(self._cache) > self._cache_num:
#                 self._cache.popitem(last=False)
#
#     def get(self, key: str) -> ThreadSafeObject:
#         if cache := self._cache.get(key):
#             cache.wait_for_loading()
#             return cache
#
#     def set(self, key: str, obj: ThreadSafeObject) -> ThreadSafeObject:
#         self._cache[key] = obj
#         self._check_count()
#         return obj
#
#     def pop(self, key: str = None) -> ThreadSafeObject:
#         if key is None:
#             return self._cache.popitem(last=False)
#         else:
#             return self._cache.pop(key, None)
#
#     def acquire(self, key: Union[str, Tuple], owner: str = "", msg: str = ""):
#         cache = self.get(key)
#         if cache is None:
#             raise RuntimeError(f"请求的资源 {key} 不存在")
#         elif isinstance(cache, ThreadSafeObject):
#             self._cache.move_to_end(key)
#             return cache.acquire(owner=owner, msg=msg)
#         else:
#             return cache
#
#
# class EmbeddingsPool(CachePool):
#     def load_embeddings(self):
#         print("初始化embedding模型")
#         from langchain.embeddings import XinferenceEmbeddings
#         self.atomic.acquire()
#         for model, server_url in server_config["online_embedding_model"].items():
#             item = ThreadSafeObject(model, pool=self)
#             self.set(model, item)
#             with item.acquire(msg="初始化"):
#                 self.atomic.release()
#                 embeddings = XinferenceEmbeddings(server_url=server_url["server_url"],
#                                                   model_uid=model)
#                 item.obj = embeddings
#                 item.finish_loading()
#
#     def get_embeddings(self, model_name: str) -> Embeddings:
#         return self.get(model_name).obj
#
#
# def load_local_embeddings(model_name: str):
#     """
#     从缓存中加载embeddings，可以避免多线程时竞争加载。
#     """
#     model_name = model_name or embedding_model
#     return embeddings_pool.get_embeddings(model_name)
#
#
# embeddings_pool = EmbeddingsPool()
