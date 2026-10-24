import threading
from collections import OrderedDict

from .thread_safe_object import ThreadSafeObject


class CachePool:
    def __init__(self, cache_num: int = 10):
        self._cache_num = cache_num
        self.cache: OrderedDict[str, ThreadSafeObject] = OrderedDict()
        self.atomic = threading.RLock()

    def keys(self) -> list[str]:
        return list(self.cache.keys())

    def _check_count(self):
        if isinstance(self._cache_num, int) and self._cache_num > 0:
            while len(self.cache) > self._cache_num:
                self.cache.popitem(last=False)

    def get(self, key: str) -> ThreadSafeObject:
        if cache := self.cache.get(key):
            cache.wait_for_loading()
            return cache

    def set(self, key: str, obj: ThreadSafeObject) -> ThreadSafeObject:
        self.cache[key] = obj
        self._check_count()
        return obj

    def pop(self, key: str = None) -> ThreadSafeObject | None:
        if key is None:
            return self.cache.popitem(last=False)[1]
        else:
            return self.cache.pop(key, None)

    def acquire(self, key: str | tuple, owner: str = '', msg: str = ''):
        cache = self.get(key)
        if cache is None:
            raise RuntimeError(f'请求的资源 {key} 不存在')
        elif isinstance(cache, ThreadSafeObject):
            self.cache.move_to_end(key)
            return cache.acquire(owner=owner, msg=msg)
        else:
            return cache
