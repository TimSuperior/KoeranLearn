from datetime import date

from fastapi import HTTPException, status
from redis import Redis

from app.core.config import get_settings


def redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def increment_daily_limit(key_prefix: str, identity: str, limit: int) -> int:
    key = f"daily:{key_prefix}:{identity}:{date.today().isoformat()}"
    try:
        redis = redis_client()
        current = redis.incr(key)
        if current == 1:
            redis.expire(key, 60 * 60 * 30)
    except Exception:
        current = 1

    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily limit exceeded for {key_prefix}",
        )
    return current
