"""Comprehensive Neighbourhood Report — Claude-powered narrative report generation.

Accepts pre-computed score data, sends to Claude with a detailed prompt,
returns structured JSON with narrative sections, scoring model, comparisons,
property tables, and relocator advice.
"""
import os
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["report"])

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

REPORT_PROMPT = """You are a senior Bangalore real estate analyst creating a VISUAL neighbourhood report. This report will be rendered as a PDF with score bars, stat cards, and bullet points — NOT paragraphs of text. Keep everything SHORT and data-dense.

CRITICAL: Respond with ONLY valid JSON. No markdown, no code fences.

{
  "neighborhood_name": "<extract neighbourhood/area name from address>",
  "headline": "<Neighbourhood> — <one-line positioning, max 10 words>",
  "composite_score": <composite_score from the data as-is, 0-100 scale, 1 decimal>,
  "executive_summary": "<Exactly 2 sentences. What makes this place special + the honest trade-off.>",
  "key_stats": [
    {"label": "Avg Price/sqft", "value": "<e.g. Rs.19,500>"},
    {"label": "Safety Rank", "value": "<e.g. Top 5 of 74>"},
    {"label": "Metro Walk", "value": "<e.g. 6 min>"},
    {"label": "Water Supply", "value": "<e.g. Stage 2, 4 hrs/day>"},
    {"label": "Rental Yield", "value": "<e.g. 2.8%>"},
    {"label": "Noise Level", "value": "<e.g. 72 dB>"}
  ],
  "sections": [
    {
      "title": "Safety & Infrastructure",
      "score": <0-100, from safety/water/power data>,
      "highlights": [
        "<short bullet, max 80 chars, with specific data — e.g. 'Top-5 safest neighbourhood; crime rate 45/100k; active CCTV + police coverage'>",
        "<bullet about water supply with stage + hours>",
        "<bullet about power with tier + outage info>",
        "<bullet about healthcare with hospital names + distance>",
        "<bullet about air quality or education>"
      ]
    },
    {
      "title": "Property & Real Estate",
      "score": <0-100>,
      "highlights": [
        "<bullet: avg price/sqft + price range>",
        "<bullet: YoY growth + appreciation trend>",
        "<bullet: rental yield vs city average>",
        "<bullet: supply dynamics or key developments>",
        "<bullet: rent-vs-buy verdict>"
      ]
    },
    {
      "title": "Transit & Connectivity",
      "score": <0-100>,
      "highlights": [
        "<bullet: nearest metro — name, distance, walk time>",
        "<bullet: key commute — nearest tech park, peak vs off-peak>",
        "<bullet: airport distance + peak travel time>",
        "<bullet: ride-hailing + auto availability>",
        "<bullet: traffic congestion assessment>"
      ]
    },
    {
      "title": "Lifestyle & Culture",
      "score": <0-100>,
      "highlights": [
        "<bullet: dining/cafe scene — name 2-3 specific spots>",
        "<bullet: nightlife character>",
        "<bullet: expat/NRI friendliness>",
        "<bullet: pet-friendliness + parks>",
        "<bullet: noise environment with dB level>"
      ]
    }
  ],
  "scoring_model": [
    {
      "category": "Livability",
      "weight_pct": 30,
      "score": <0-100, 1 decimal>,
      "subcategories": [
        {"name": "Safety", "score": <0-100>},
        {"name": "Healthcare", "score": <0-100>},
        {"name": "Education", "score": <0-100>},
        {"name": "Air quality", "score": <0-100>},
        {"name": "Infrastructure", "score": <0-100>}
      ]
    },
    {
      "category": "Transit & Connectivity",
      "weight_pct": 25,
      "score": <0-100>,
      "subcategories": [
        {"name": "Metro", "score": <0-100>},
        {"name": "Bus", "score": <0-100>},
        {"name": "Ride-hailing", "score": <0-100>},
        {"name": "Traffic", "score": <0-100>},
        {"name": "Employment", "score": <0-100>}
      ]
    },
    {
      "category": "Real Estate Value",
      "weight_pct": 20,
      "score": <0-100>,
      "subcategories": [
        {"name": "Appreciation", "score": <0-100>},
        {"name": "Future growth", "score": <0-100>},
        {"name": "Rental yield", "score": <0-100>},
        {"name": "Supply-demand", "score": <0-100>},
        {"name": "Infra impact", "score": <0-100>}
      ]
    },
    {
      "category": "Lifestyle & Culture",
      "weight_pct": 15,
      "score": <0-100>,
      "subcategories": [
        {"name": "Dining", "score": <0-100>},
        {"name": "Cafes", "score": <0-100>},
        {"name": "Expat-friendly", "score": <0-100>},
        {"name": "Pet-friendly", "score": <0-100>},
        {"name": "Weekend life", "score": <0-100>}
      ]
    },
    {
      "category": "Walkability",
      "weight_pct": 10,
      "score": <0-100>,
      "subcategories": [
        {"name": "Destinations", "score": <0-100>},
        {"name": "Sidewalks", "score": <0-100>},
        {"name": "Cycling", "score": <0-100>},
        {"name": "Pedestrian safety", "score": <0-100>}
      ]
    }
  ],
  "property_table": [
    {"config": "1 BHK", "purchase_range": "Rs.XL - Rs.Y Cr", "rent_range": "Rs.X,000 - Rs.Y,000"},
    {"config": "2 BHK", "purchase_range": "...", "rent_range": "..."},
    {"config": "3 BHK", "purchase_range": "...", "rent_range": "..."}
  ],
  "comparisons": [
    {"name": "<neighbourhood>", "composite": <0-100>, "strongest_edge": "<max 30 chars>", "biggest_gap": "<max 30 chars>"},
    {"name": "...", "composite": 0, "strongest_edge": "...", "biggest_gap": "..."},
    {"name": "...", "composite": 0, "strongest_edge": "...", "biggest_gap": "..."},
    {"name": "...", "composite": 0, "strongest_edge": "...", "biggest_gap": "..."}
  ],
  "bottom_line": "<2-3 sentences. Who should live here, who shouldn't, pricing context.>",
  "pro_tip": "<1 sentence. Specific practical advice for relocators.>"
}

RULES:
1. Use Rs. for prices (not ₹ — PDF can't render it).
2. ALL scores are 0-100 scale (matching the sidebar). Use the data scores directly as baseline, adjust ±5 with your knowledge.
3. Each bullet in highlights: MAX 90 characters. Data-dense, no filler words.
4. key_stats: extract the 6 most important metrics. Use the actual data values.
5. Be HONEST. Scores below 40/100 = call it out. Don't sugarcoat.
6. Name specific local spots (restaurants, hospitals, parks, roads) where you know them.
7. If you don't know a lesser-known area's local spots, focus on data. Never invent names.
8. comparisons: 4-5 competing neighbourhoods with honest composites.
9. property_table: derive from avg_price_sqft and avg_2bhk data. Extrapolate 1BHK/3BHK.
10. Total response should be CONCISE — this is a visual report, not an essay."""


class ReportInput(BaseModel):
    score_data: dict[str, Any]


@router.post("/generate-report")
async def generate_report(input: ReportInput):
    """Generate a comprehensive neighbourhood report using Claude AI."""
    try:
        import anthropic
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="AI service not available — anthropic package not installed",
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured — set ANTHROPIC_API_KEY",
        )

    score_json = json.dumps(input.score_data, indent=2, default=str)
    client = anthropic.AsyncAnthropic(api_key=api_key)

    max_retries = 2
    last_error = None

    for attempt in range(max_retries):
        try:
            message = await client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": f"{REPORT_PROMPT}\n\nNEIGHBOURHOOD SCORE DATA:\n{score_json}",
                }],
            )

            raw = message.content[0].text.strip()  # type: ignore[union-attr]

            if raw.startswith("```"):
                first_newline = raw.find("\n")
                if first_newline != -1:
                    raw = raw[first_newline + 1:]
                else:
                    raw = raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3].strip()

            report = json.loads(raw)
            return report

        except (json.JSONDecodeError, IndexError, KeyError) as e:
            last_error = e
            logger.error(f"Claude returned unparseable response on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(2)
                continue
            raise HTTPException(
                status_code=500,
                detail="Report generation failed — AI returned invalid format. Please try again.",
            )
        except Exception as e:
            last_error = e
            error_name = type(e).__name__
            if "overloaded" in str(e).lower() or "rate" in str(e).lower():
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(4)
                    continue
            logger.error(f"Report generation failed: {error_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Report generation failed: {error_name}",
            )

    raise HTTPException(
        status_code=500,
        detail=f"Report generation failed after {max_retries} attempts: {last_error}",
    )
