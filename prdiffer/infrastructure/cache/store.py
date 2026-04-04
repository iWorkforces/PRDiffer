"""Cache storage and LRU eviction logic."""

import time
from collections import OrderedDict
from typing import Any


class CacheStore:
    """LRU cache storage with TTL and size-based eviction."""

    def __init__(self, max_size: int = 1000, ttl: int = 600):
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def ttl(self) -> int:
        return self._ttl

    def get(self, key: str) -> dict[str, Any] | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, data: dict[str, Any]) -> None:
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._max_size:
            self._evict_oldest()

        self._cache[key] = data
        self._cache.move_to_end(key)

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()

    def keys(self) -> list[str]:
        return list(self._cache.keys())

    def _evict_oldest(self) -> None:
        if self._cache:
            self._cache.popitem(last=False)

    def is_expired(self, entry: dict[str, Any]) -> bool:
        timestamp = entry.get("timestamp")
        if timestamp is None:
            return False
        return time.time() - float(timestamp) > self._ttl

    def evict_expired(self) -> list[str]:
        current_time = time.time()
        expired_keys: list[str] = []

        for key, entry in list(self._cache.items()):
            age = current_time - float(entry.get("timestamp", 0))
            if age >= self._ttl:
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)

        return expired_keys
