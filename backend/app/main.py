import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from app.db import close_pool, get_pool  # noqa: E402
from app.routers.ai_chat import router as ai_chat_router  # noqa: E402
from app.routers.property_intelligence import router as property_intelligence_router  # noqa: E402
from app.routers.report import router as report_router  # noqa: E402
from app.routers.scores import router as scores_router  # noqa: E402

# ---------------------------------------------------------------------------
# Lightweight per-IP rate limiter (token bucket, no external deps)
# ---------------------------------------------------------------------------
_RATE_LIMITS: dict[str, tuple[int, float]] = {
    # path prefix -> (max_tokens, refill_per_second)
    "/api/ai-chat": (10, 0.5),  # 10 burst, 1 every 2s
    "/api/report": (5, 0.2),  # 5 burst, 1 every 5s
    "/api/scores": (30, 2.0),  # 30 burst, 2/s
    "/api/verify-claims": (10, 0.5),
}
_DEFAULT_LIMIT = (60, 5.0)  # generous default

_buckets: dict[str, dict[str, list]] = defaultdict(dict)  # ip -> {prefix: [tokens, last_refill]}


def _check_rate_limit(ip: str, path: str) -> bool:
    """Return True if the request is allowed."""
    # Find matching prefix
    max_tokens, refill_rate = _DEFAULT_LIMIT
    for prefix, limits in _RATE_LIMITS.items():
        if path.startswith(prefix):
            max_tokens, refill_rate = limits
            break
    else:
        prefix = "__default__"

    now = time.monotonic()
    bucket = _buckets[ip]
    if prefix not in bucket:
        bucket[prefix] = [float(max_tokens), now]

    tokens, last = bucket[prefix]
    # Refill tokens
    tokens = min(max_tokens, tokens + (now - last) * refill_rate)
    bucket[prefix][1] = now

    if tokens >= 1.0:
        bucket[prefix][0] = tokens - 1.0
        return True
    bucket[prefix][0] = tokens
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_pool()
    except Exception:
        # DB may be temporarily unavailable — app starts anyway,
        # pool is created lazily on first request.
        pass
    yield
    await close_pool()


app = FastAPI(
    title="Neighbourhood Score API",
    description=(
        "Data-driven neighborhood scoring for Bangalore home buyers. "
        "Research-backed methodologies: CPCB AQI, NEWS-India walkability, "
        "MOHUA TOD transit norms, IPHS hospital standards, RTE school norms, "
        "RBI affordability, RERA builder compliance. "
        "AI-verified with Claude for data quality assurance."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip, request.url.path):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
        )
    return await call_next(request)


app.include_router(scores_router)
app.include_router(ai_chat_router)
app.include_router(report_router)
app.include_router(property_intelligence_router)


@app.get("/")
async def root():
    return {
        "service": "Neighbourhood Score",
        "version": "2.0.0",
        "methodology": {
            "air_quality": "CPCB National AQI (2014)",
            "walkability": "NEWS-India (Sallis et al. 2016)",
            "transit": "MOHUA TOD Policy (2017) — 500m/800m norms",
            "safety": "MOHUA EoLI Safety Pillar + NARI 2025",
            "hospital": "IPHS 2022 (MoHFW)",
            "school": "RTE Act 2009 Section 6 — 1km/3km norms",
            "affordability": "RBI EMI/Income ratio + ANAROCK H1 2025",
            "water": "BWSSB Stage-wise classification",
            "power": "BESCOM tier classification",
            "composite_weights": "ANAROCK Homebuyer Sentiment Survey H1 2025",
        },
        "ai_verification": "Claude background verification (sanity + freshness + narrative)",
        "data_sources": [
            "PostgreSQL + PostGIS (Supabase)",
            "OpenStreetMap Overpass API",
            "CPCB Air Quality Monitoring",
            "data.opencity.in (CC BY 4.0)",
            "RERA Karnataka Portal",
        ],
    }
