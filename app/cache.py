import hashlib
import json
import logging
import os

import redis
from dotenv import load_dotenv
from redis.exceptions import RedisError

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def task_list_cache_key(
    user_id: int,
    version: int,
    completed: bool | None,
    keyword: str | None,
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
) -> str:
    """为用户和查询条件生成唯一缓存键。"""
    params = {
        "completed": completed,
        "keyword": keyword.strip() if keyword else None,
        "page": page,
        "page_size": page_size,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"tasks:list:{user_id}:v{version}:{digest}"


def get_task_cache_version(user_id: int) -> int | None:
    """读取用户缓存版本；Redis 不可用时返回 None。"""
    try:
        value = redis_client.get(f"tasks:version:{user_id}")
        return int(value) if value is not None else 0
    except (RedisError, ValueError, TypeError):
        logger.warning("Redis 缓存版本读取失败", exc_info=True)
        return None


def get_cached_task_page(key: str) -> str | None:
    try:
        return redis_client.get(key)
    except RedisError:
        logger.warning("Redis 缓存读取失败", exc_info=True)
        return None


def set_cached_task_page(key: str, data: str) -> None:
    try:
        redis_client.setex(key, CACHE_TTL_SECONDS, data)
    except RedisError:
        logger.warning("Redis 缓存写入失败", exc_info=True)


def invalidate_task_cache(user_id: int) -> None:
    """更新用户缓存版本，让旧版本的缓存键失效。"""
    try:
        redis_client.incr(f"tasks:version:{user_id}")
    except RedisError:
        logger.warning("Redis 缓存失效操作失败", exc_info=True)