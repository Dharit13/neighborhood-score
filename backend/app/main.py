from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.db import get_pool, close_pool
from app.routers.scores import router as scores_router
from app.routers.ai_chat import router as ai_chat_router
from app.routers.report import router as report_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scores_router)
app.include_router(ai_chat_router)
app.include_router(report_router)


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
