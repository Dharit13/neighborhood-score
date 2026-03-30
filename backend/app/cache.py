"""Shared Redis cache — used across workers for geocode results, AI responses, rate limits.

Falls back to in-memory dicts when REDIS_URL is not set (local dev).
"""

import hashlib
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")

_redis = None
_fallback: dict[str, tuple[str, float]] = {}  # key -> (json_value, expire_at)


async def _get_redis():
    """Lazy-init async Redis connection."""
    global _redis
    if _redis is not None:
        return _redis
    if not REDIS_URL:
        return None
    try:
        from redis.asyncio import from_url  # type: ignore

        _redis = from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
        await _redis.ping()
        logger.info("Redis connected")
        return _redis
    except Exception as e:
        logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
        _redis = None
        return None


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def make_key(namespace: str, *parts: str) -> str:
    """Build a cache key like 'ns:sha256[:16]'."""
    raw = ":".join(str(p) for p in parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{namespace}:{h}"


async def get(key: str) -> str | None:
    """Get a cached value. Returns None on miss or error."""
    r = await _get_redis()
    if r:
        try:
            return await r.get(key)
        except Exception:
            pass
    # Fallback
    entry = _fallback.get(key)
    if entry and entry[1] > time.monotonic():
        return entry[0]
    if entry:
        del _fallback[key]
    return None


async def set(key: str, value: str, ttl: int = 300) -> None:
    """Set a cached value with TTL in seconds."""
    r = await _get_redis()
    if r:
        try:
            await r.setex(key, ttl, value)
            return
        except Exception:
            pass
    # Fallback — cap at 500 entries
    if len(_fallback) >= 500:
        now = time.monotonic()
        expired = [k for k, v in _fallback.items() if v[1] <= now]
        for k in expired:
            del _fallback[k]
        if len(_fallback) >= 500:
            oldest = min(_fallback, key=lambda k: _fallback[k][1])
            del _fallback[oldest]
    _fallback[key] = (value, time.monotonic() + ttl)


async def get_json(key: str):
    """Get and JSON-decode a cached value."""
    raw = await get(key)
    if raw is not None:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


async def set_json(key: str, value, ttl: int = 300) -> None:
    """JSON-encode and cache a value."""
    await set(key, json.dumps(value, default=str), ttl)


# ---------------------------------------------------------------------------
# Rate limiter backed by Redis (shared across workers)
# ---------------------------------------------------------------------------
async def check_rate_limit(
    ip: str, path: str, limits: dict[str, tuple[int, float]], default: tuple[int, float]
) -> bool:
    """Token-bucket rate limiter. Returns True if allowed.

    Uses Redis MULTI for atomic check-and-decrement across workers.
    Falls back to in-memory when Redis is unavailable.
    """
    max_tokens, refill_rate = default
    prefix = "__default__"
    for pfx, lim in limits.items():
        if path.startswith(pfx):
            max_tokens, refill_rate = lim
            prefix = pfx
            break

    bucket_key = f"rl:{ip}:{prefix}"

    r = await _get_redis()
    if r:
        try:
            # Lua script for atomic token bucket
            lua = """
            local key = KEYS[1]
            local max_t = tonumber(ARGV[1])
            local refill = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local ttl = tonumber(ARGV[4])

            local data = redis.call('GET', key)
            local tokens, last
            if data then
                local sep = string.find(data, ':')
                tokens = tonumber(string.sub(data, 1, sep-1))
                last = tonumber(string.sub(data, sep+1))
            else
                tokens = max_t
                last = now
            end

            tokens = math.min(max_t, tokens + (now - last) * refill)

            if tokens >= 1 then
                tokens = tokens - 1
                redis.call('SETEX', key, ttl, tokens .. ':' .. now)
                return 1
            else
                redis.call('SETEX', key, ttl, tokens .. ':' .. now)
                return 0
            end
            """
            result = await r.eval(lua, 1, bucket_key, str(max_tokens), str(refill_rate), str(time.time()), "120")
            return bool(result)
        except Exception:
            pass

    # In-memory fallback (same logic as before)
    now = time.monotonic()
    entry = _fallback.get(bucket_key)
    if entry:
        try:
            data = json.loads(entry[0])
            tokens, last = data["t"], data["l"]
        except (json.JSONDecodeError, KeyError):
            tokens, last = float(max_tokens), now
    else:
        tokens, last = float(max_tokens), now

    tokens = min(max_tokens, tokens + (now - last) * refill_rate)
    if tokens >= 1.0:
        tokens -= 1.0
        _fallback[bucket_key] = (json.dumps({"t": tokens, "l": now}), now + 120)
        return True
    _fallback[bucket_key] = (json.dumps({"t": tokens, "l": now}), now + 120)
    return False
