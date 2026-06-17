"""内存缓存（带 TTL）。"""
from __future__ import annotations

import time
from typing import Any, Optional

# _cache[key] = (stored_ts, value)
_cache: dict[str, tuple[float, Any]] = {}


def get(key: str, ttl: Optional[float] = None) -> Optional[Any]:
    """获取缓存值。

    - 传入 ttl：按 ttl 秒检查是否过期
    - 不传 ttl：永不过期（仅在显式删除时失效）
    """
    item = _cache.get(key)
    if item is None:
        return None
    ts, val = item
    if ttl is not None and time.time() - ts >= ttl:
        _cache.pop(key, None)
        return None
    return val


def set(key: str, val: Any) -> None:
    """写入缓存（覆盖旧值）。时间戳由 set 写入，TTL 在 get 时检查。"""
    _cache[key] = (time.time(), val)


def pop(key: str) -> None:
    """显式删除某个 key。"""
    _cache.pop(key, None)


def clear() -> None:
    """清空缓存（用于测试）。"""
    _cache.clear()
