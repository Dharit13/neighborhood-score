"""AI Chat endpoint — wraps Claude with neighborhood data context for Q&A."""

import asyncio
import json
import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.db import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

SYSTEM_PROMPT = """You are a helpful Bangalore real estate advisor. You have access to scored data
for 74 neighborhoods across 17 dimensions (safety, transit, commute, schools,
hospitals, air quality, water, power, flood risk, noise, walkability, cleanliness,
property prices, builder reputation, future infrastructure, delivery, business).

{context}

IMPORTANT: You answer questions about Bangalore neighborhoods and anything
related to living in Bangalore — schools, hospitals, safety, transit, commute,
parks, restaurants, nightlife, noise, air quality, water, power, flood risk,
builders, property prices, rent, investment, infrastructure, delivery, business,
walkability, cleanliness, lifestyle, family-friendliness, and similar topics.
These are ALL valid questions you should answer helpfully.

Only REFUSE questions that are completely unrelated to Bangalore or city living
(e.g., coding help, math homework, writing essays, stock trading, recipes,
relationship advice). For those, briefly say: "I'm focused on Bangalore
neighborhoods and real estate — try asking about a specific area or comparing
neighborhoods!"

RESPONSE RULES:
- Maximum 3-5 sentences total. Never exceed this.
- Use numbers from the data. Use ₹ for prices.
- Do NOT ask follow-up questions back to the user.
- Do NOT list what you could help with.
- Do NOT explain what data you lack — just answer with what you have.
- If data is missing for a dimension, skip it silently. NEVER say "I don't have", "not available", "not in my data", or similar disclaimers.
- Go straight to the answer. No preambles."""


class AIChatInput(BaseModel):
    message: str
    neighborhood: str | None = None
    latitude: float | None = None
    longitude: float | None = None


async def _get_neighborhood_summary(name: str) -> dict | None:
    """Fetch full score data for a specific neighborhood."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT n.id, n.name,
                          sz.score as safety_score, sz.crime_rate_per_100k,
                          wz.score as walkability_score,
                          wtz.score as water_score, wtz.stage as water_stage,
                          pz.score as power_score, pz.tier as power_tier,
                          fr.score as flood_score, fr.risk_level as flood_risk,
                          pp.affordability_score, pp.avg_price_sqft, pp.avg_2bhk_lakh,
                          pp.avg_2bhk_rent, pp.yoy_growth_pct, pp.rental_yield_pct,
                          bo.score as business_score,
                          nz.score as noise_score, nz.avg_noise_db_estimate, nz.noise_label,
                          dc.coverage_score as delivery_score,
                          nv.narrative as ai_narrative, nv.confidence as ai_confidence
                   FROM neighborhoods n
                   LEFT JOIN safety_zones sz ON sz.neighborhood_id = n.id
                   LEFT JOIN walkability_zones wz ON wz.neighborhood_id = n.id
                   LEFT JOIN water_zones wtz ON wtz.neighborhood_id = n.id
                   LEFT JOIN power_zones pz ON pz.neighborhood_id = n.id
                   LEFT JOIN flood_risk fr ON fr.neighborhood_id = n.id
                   LEFT JOIN property_prices pp ON pp.neighborhood_id = n.id
                   LEFT JOIN business_opportunity bo ON bo.neighborhood_id = n.id
                   LEFT JOIN noise_zones nz ON nz.neighborhood_id = n.id
                   LEFT JOIN delivery_coverage dc ON dc.neighborhood_id = n.id
                   LEFT JOIN neighborhood_verification nv ON nv.neighborhood_id = n.id
                   WHERE LOWER(n.name) LIKE '%' || LOWER($1) || '%'
                   LIMIT 1""",
                name,
            )
        if row:
            return {k: (float(v) if isinstance(v, (int, float)) and v is not None else v) for k, v in dict(row).items()}
    except Exception as e:
        logger.warning(f"Neighborhood summary fetch failed: {e}")
    return None


async def _get_all_neighborhoods_summary() -> list[dict]:
    """Fetch condensed summary of all neighborhoods for recommendation queries."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT n.name,
                       sz.score as safety, wz.score as walkability,
                       wtz.score as water, pz.score as power,
                       fr.score as flood, pp.affordability_score as affordability,
                       pp.avg_price_sqft, pp.avg_2bhk_lakh, pp.avg_2bhk_rent,
                       pp.yoy_growth_pct,
                       bo.score as business,
                       nz.score as noise, nz.noise_label,
                       dc.coverage_score as delivery
                FROM neighborhoods n
                LEFT JOIN safety_zones sz ON sz.neighborhood_id = n.id
                LEFT JOIN walkability_zones wz ON wz.neighborhood_id = n.id
                LEFT JOIN water_zones wtz ON wtz.neighborhood_id = n.id
                LEFT JOIN power_zones pz ON pz.neighborhood_id = n.id
                LEFT JOIN flood_risk fr ON fr.neighborhood_id = n.id
                LEFT JOIN property_prices pp ON pp.neighborhood_id = n.id
                LEFT JOIN business_opportunity bo ON bo.neighborhood_id = n.id
                LEFT JOIN noise_zones nz ON nz.neighborhood_id = n.id
                LEFT JOIN delivery_coverage dc ON dc.neighborhood_id = n.id
                ORDER BY n.name
            """)
        return [
            {k: (float(v) if isinstance(v, (int, float)) and v is not None else v) for k, v in dict(r).items()}
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"All neighborhoods summary failed: {e}")
    return []


@router.post("/ai-chat")
async def ai_chat(input: AIChatInput):
    """AI-powered neighborhood Q&A using Claude."""
    try:
        import anthropic
    except ImportError:
        return JSONResponse(
            status_code=503,
            content={
                "error": "AI service not available",
                "detail": "The anthropic package is not installed on the server.",
            },
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse(
            status_code=503,
            content={
                "error": "AI service not configured",
                "detail": "Set ANTHROPIC_API_KEY in backend .env to enable AI chat.",
            },
        )

    # Build context
    context_parts = []
    if input.neighborhood:
        data = await _get_neighborhood_summary(input.neighborhood)
        if data:
            context_parts.append(
                f"Current neighborhood data for {input.neighborhood}:\n{json.dumps(data, indent=2, default=str)}"
            )

    if not context_parts:
        all_data = await _get_all_neighborhoods_summary()
        if all_data:
            context_parts.append(
                f"Summary data for all {len(all_data)} neighborhoods:\n{json.dumps(all_data, indent=2, default=str)}"
            )

    context = "\n\n".join(context_parts) if context_parts else "No neighborhood data currently loaded."
    system = SYSTEM_PROMPT.format(context=context)

    # Use async client for non-blocking streaming
    client = anthropic.AsyncAnthropic(api_key=api_key)

    async def stream_response():
        try:
            async with client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=250,
                system=system,
                messages=[{"role": "user", "content": input.message}],
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
                    await asyncio.sleep(0)
            yield "data: [DONE]\n\n"
        except anthropic.APIConnectionError:
            yield f"data: {json.dumps({'error': 'AI service is temporarily unavailable. Please try again.'})}\n\n"
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'error': 'AI service is not configured. Please contact support.'})}\n\n"
        except anthropic.RateLimitError:
            yield f"data: {json.dumps({'error': 'AI is busy. Please try again in a moment.'})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'error': 'Something went wrong. Please try again.'})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
