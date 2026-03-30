import asyncio
import hashlib
import logging
import time

import httpx

logger = logging.getLogger(__name__)

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

MAX_RETRIES = 3
BACKOFF_BASE = 1.5

_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL_SECONDS = 600


def _cache_key(query: str) -> str:
    return hashlib.md5(query.encode(), usedforsecurity=False).hexdigest()


async def query_overpass(query: str) -> list[dict]:
    key = _cache_key(query)
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return data
        del _cache[key]

    for url in OVERPASS_MIRRORS:
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=50.0) as client:
                    resp = await client.post(url, data={"data": query})

                    if resp.status_code == 200:
                        data = resp.json()
                        elements = data.get("elements", [])
                        _cache[key] = (time.time(), elements)
                        return elements

                    if resp.status_code == 429:
                        wait = BACKOFF_BASE ** (attempt + 1)
                        logger.warning(f"Overpass 429 from {url}, backing off {wait:.1f}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait)
                        continue

                    if resp.status_code in (504, 503, 502):
                        wait = BACKOFF_BASE**attempt
                        logger.warning(f"Overpass {resp.status_code} from {url}, retrying in {wait:.1f}s")
                        await asyncio.sleep(wait)
                        continue

                    logger.warning(f"Overpass {url} returned {resp.status_code}")
                    break

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"Overpass {url} failed: {type(e).__name__}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE**attempt)
                continue

    return []


def parse_elements(elements: list[dict]) -> list[dict]:
    results = []
    for el in elements:
        lat = el.get("lat") or (el.get("center", {}).get("lat"))
        lon = el.get("lon") or (el.get("center", {}).get("lon"))
        if lat is None or lon is None:
            continue
        tags = el.get("tags", {})
        name = tags.get("name", "Unnamed")
        category = tags.get("amenity") or tags.get("shop") or tags.get("leisure") or "unknown"
        results.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "category": category,
            }
        )
    return results
