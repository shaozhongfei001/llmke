import threading
from contextlib import contextmanager
from typing import Any, TYPE_CHECKING

from log import logger

if TYPE_CHECKING:
    from .cache_pool import CachePool


class ThreadSafeObject:
    def __init__(self, key: str | tuple, obj: Any = None, pool: 'CachePool' = None):
        self._obj = obj
        self._key = key
        self._pool = pool
        self._lock = threading.RLock()
        self._loaded = threading.Event()

    def __repr__(self) -> str:
        cls = type(self).__name__
        return f"<{cls}: key: {self.key}, obj: {self._obj}>"

    @property
    def key(self):
        return self._key

    @contextmanager
    def acquire(self, owner: str = '', msg: str = ''):
        owner = owner or f'thread {threading.get_native_id()}'
        try:
            self._lock.acquire()
            if self._pool is not None:
                self._pool.cache.move_to_end(self.key)
            logger.info(f"{owner} 开始操作：{self.key}。{msg}")
            yield self._obj
        finally:
            logger.info(f"{owner} 结束操作：{self.key}。{msg}")
            self._lock.release()

    def start_loading(self):
        self._loaded.clear()

    def finish_loading(self):
        self._loaded.set()

    def wait_for_loading(self):
        self._loaded.wait()

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, val: Any):
        self._obj = val
