# services/cache.py
import json
from typing import Any, Dict, Optional, List, Set, Tuple
import asyncio
from datetime import datetime, timedelta
import hashlib


class CacheService:
    """缓存服务"""

    def __init__(self):
        """初始化缓存服务"""
        self.cache = {}
        self.expiry = {}
        self._cleanup_task = None

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 检查是否过期
        if key in self.expiry and datetime.now() > self.expiry[key]:
            # 过期了，删除并返回None
            del self.cache[key]
            del self.expiry[key]
            return None

        # 返回缓存值
        return self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        self.cache[key] = value
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl)

        # 启动清理任务
        self._ensure_cleanup_task()

    async def delete(self, key: str) -> None:
        """删除缓存值"""
        if key in self.cache:
            del self.cache[key]
        if key in self.expiry:
            del self.expiry[key]

    async def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.expiry.clear()

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """获取多个缓存值"""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value

        return result

    async def set_many(self, values: Dict[str, Any], ttl: int = 3600) -> None:
        """设置多个缓存值"""
        for key, value in values.items():
            await self.set(key, value, ttl)

    async def delete_many(self, keys: List[str]) -> None:
        """删除多个缓存值"""
        for key in keys:
            await self.delete(key)

    def _ensure_cleanup_task(self) -> None:
        """确保清理任务运行"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup())

    async def _cleanup(self) -> None:
        """定期清理过期缓存"""
        while True:
            # 等待一段时间
            await asyncio.sleep(60)  # 每分钟检查一次

            now = datetime.now()
            expired_keys = [key for key, expire_time in self.expiry.items() if now > expire_time]

            # 删除过期的项
            for key in expired_keys:
                await self.delete(key)

    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 对参数进行排序，以确保相同的参数生成相同的键
        key_parts = [prefix]

        if args:
            key_parts.append(json.dumps(args, sort_keys=True))

        if kwargs:
            key_parts.append(json.dumps(kwargs, sort_keys=True))

        # 组合并哈希，生成固定长度的键
        combined = ":".join(key_parts)
        return f"{prefix}:{hashlib.md5(combined.encode()).hexdigest()}"


# 全局缓存实例
cache = CacheService()


def get_cache():
    """获取缓存服务"""
    return cache