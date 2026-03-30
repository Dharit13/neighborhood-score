"""
Property Intelligence API routes.

New endpoints for the property intelligence platform:
  - GET /api/builders — list builders by area/tier
  - GET /api/builder/:slug — full builder profile
  - GET /api/area/:slug — full area profile
  - POST /api/intelligence-brief — AI-generated buyer advisory
  - GET /api/infrastructure — infrastructure projects
  - GET /api/search — global search
"""

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import require_auth
from app.db import get_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["property-intelligence"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


# ============================================================
# Response models
# ============================================================


class BuilderSummary(BaseModel):
    name: str
    slug: str | None = None
    trust_score: int | None = None
    trust_tier: str | None = None
    segment: str | None = None
    rera_projects: int = 0
    complaints: int = 0
    complaints_ratio: float = 0
    on_time_delivery_pct: int = 0
    avg_rating: float | None = None
    active_areas: list[str] = []
    notable_projects: list[str] = []


class BuilderProfile(BuilderSummary):
    also_known_as: list[str] = []
    cin: str | None = None
    company_status: str | None = None
    incorporated_date: str | None = None
    has_nclt_proceedings: bool = False
    nclt_case_details: str | None = None
    consumer_court_cases: int = 0
    director_names: list[str] = []
    directors_linked_to_failed: bool = False
    director_risk_details: str | None = None
    review_sentiment_score: float | None = None
    common_complaints: list[str] = []
    common_praise: list[str] = []
    trust_score_breakdown: dict | None = None
    description: str | None = None
    founded_year: int | None = None
    website: str | None = None
    certifications: list[str] = []
    data_source: str | None = None
    projects: list[dict] = []
    risk_flags: list[dict] = []


class IntelligenceBriefRequest(BaseModel):
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    claims: list[str] = []


BUILDER_SUMMARY_PROMPT = """You are a sharp Bangalore real estate analyst helping home buyers evaluate builders. Given data about builders active in a specific area, produce two things:

1. **area_summary**: A 2-4 sentence overview of the builder landscape in this area. Mention the strongest builders by name, flag any with NCLT/legal issues, and give a quick buyer recommendation. Be direct and specific — name names, cite numbers.

2. **builder_briefs**: For each builder, write a 2-3 sentence buyer-focused brief. Cover their track record, market reputation, notable projects, and any red flags. Use the provided data as your primary source but supplement with your knowledge of Bangalore builders (their reputation, market position, build quality, known issues). Be honest — if a builder has problems, say so.

Guidelines:
- Write in 2nd person ("you", "your investment") — you're talking to a buyer.
- Use actual numbers from the data (trust score, on-time %, complaint count, RERA projects).
- Supplement with your knowledge: builder history, known projects, market segment reputation, build quality reputation.
- For builders you know well from your training, add insights the data doesn't cover (e.g., "known for premium finishes", "has a history of delayed possession in other cities").
- If you don't know a builder, stick to the data provided.
- Don't sugarcoat — if a builder has issues, be direct about it.
- Keep each brief concise. No bullet points, no markdown.

Respond with ONLY a JSON object in this format:
{
  "area_summary": "Your 2-4 sentence area overview...",
  "builder_briefs": {
    "builder-slug-1": "2-3 sentence brief...",
    "builder-slug-2": "2-3 sentence brief..."
  }
}

No markdown, no explanation outside the JSON."""


async def _generate_builder_summaries(
    area: str | None,
    rows: list,
) -> tuple[str | None, dict[str, str]]:
    """Generate AI area summary and per-builder briefs in a single Claude call."""
    if not ANTHROPIC_API_KEY:
        return None, {}
    if not rows and not area:
        return None, {}

    area_label = (area or "this area").replace("-", " ").title()

    if not rows:
        context = f"Area: {area_label}\n\nNo builders found in our database for this area. Use your knowledge of Bangalore real estate builders who are active or have projects in or near {area_label}. Include major developers like Prestige, Brigade, Sobha, Godrej, Puravankara, Salarpuria, Mantri, etc. if they have projects there. For builder_briefs, use the builder name in lowercase with spaces replaced by hyphens as the key."
    else:
        builder_lines = []
        for r in rows:
            line = {
                "name": r["name"],
                "slug": r["slug"] or r["name"].lower().replace(" ", "-"),
                "trust_score": r["trust_score"],
                "trust_tier": r["trust_tier"] or "unscored",
                "segment": r["segment"] or r["reputation_tier"],
                "rera_projects": r["rera_projects"],
                "complaints": r["complaints"],
                "complaints_ratio": float(r["complaints_ratio"]) if r["complaints_ratio"] else 0,
                "on_time_delivery_pct": r["on_time_delivery_pct"],
                "avg_rating": float(r["avg_rating"]) if r["avg_rating"] else None,
                "has_nclt_proceedings": r.get("has_nclt_proceedings", False),
                "nclt_case_details": r.get("nclt_case_details"),
                "notable_projects": r.get("notable_projects") or [],
                "common_complaints": r.get("common_complaints") or [],
                "common_praise": r.get("common_praise") or [],
            }
            builder_lines.append(line)

        context = f"Area: {area_label}\n\nBuilders ({len(builder_lines)}):\n"
        context += json.dumps(builder_lines, indent=2, default=str)

    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1500,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{BUILDER_SUMMARY_PROMPT}\n\n{context}",
                        }
                    ],
                },
            )

            if resp.status_code != 200:
                logger.warning(f"Builder summary AI error {resp.status_code}")
                return None, {}

            data = resp.json()
            text = data["content"][0]["text"].strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            parsed = json.loads(text)
            return (
                parsed.get("area_summary"),
                parsed.get("builder_briefs", {}),
            )

    except Exception as e:
        logger.warning(f"Builder summary generation failed: {e}")
        return None, {}


# ============================================================
# GET /api/builders
# ============================================================


@router.get("/builders")
async def list_builders(
    area: str | None = Query(None, description="Filter by area slug or name"),
    tier: str | None = Query(None, description="Filter by trust tier: trusted, emerging, cautious, avoid"),
    segment: str | None = Query(
        None, description="Filter by segment: premium, established, mid-range, affordable, luxury"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    _user: dict = Depends(require_auth),
):
    """List builders, optionally filtered by area, tier, or segment."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []
        param_idx = 0

        if area:
            param_idx += 1
            conditions.append(f"""(
                ${param_idx} = ANY(active_areas)
                OR EXISTS (SELECT 1 FROM unnest(active_areas) a WHERE LOWER(a) LIKE '%' || LOWER(${param_idx}) || '%')
                OR EXISTS (SELECT 1 FROM unnest(active_areas) a WHERE LOWER(${param_idx}) LIKE '%' || LOWER(a) || '%')
            )""")
            params.append(area.replace("-", " "))

        if tier:
            param_idx += 1
            conditions.append(f"trust_tier = ${param_idx}")
            params.append(tier)

        if segment:
            param_idx += 1
            conditions.append(f"(segment = ${param_idx} OR reputation_tier = ${param_idx})")
            params.append(segment)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM builders {where}"
        total_count = await conn.fetchval(count_query, *params)

        limit_param = param_idx + 1
        offset_param = param_idx + 2
        param_idx += 2
        query = f"""
            SELECT name, slug, trust_score, trust_tier, segment, reputation_tier,
                   rera_projects, complaints, complaints_ratio,
                   on_time_delivery_pct, avg_rating, active_areas, notable_projects,
                   trust_score_breakdown, has_nclt_proceedings, nclt_case_details,
                   common_complaints, common_praise, description
            FROM builders
            {where}
            ORDER BY COALESCE(trust_score, score, 0) DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        params.append(limit)
        params.append(offset)

        rows = await conn.fetch(query, *params)

    # Group by tier
    grouped = {"trusted": [], "emerging": [], "cautious": [], "avoid": [], "unscored": []}
    for r in rows:
        tier_key = r["trust_tier"] or "unscored"
        if tier_key not in grouped:
            tier_key = "unscored"
        grouped[tier_key].append(
            {
                "name": r["name"],
                "slug": r["slug"],
                "trust_score": r["trust_score"],
                "trust_tier": r["trust_tier"],
                "segment": r["segment"] or r["reputation_tier"],
                "rera_projects": r["rera_projects"],
                "complaints": r["complaints"],
                "complaints_ratio": float(r["complaints_ratio"]) if r["complaints_ratio"] else 0,
                "on_time_delivery_pct": r["on_time_delivery_pct"],
                "avg_rating": float(r["avg_rating"]) if r["avg_rating"] else None,
                "active_areas": r["active_areas"] or [],
                "notable_projects": r["notable_projects"] or [],
                "trust_score_breakdown": json.loads(r["trust_score_breakdown"]) if r["trust_score_breakdown"] else None,
            }
        )

    # Generate AI summaries (area-level + per-builder briefs)
    area_summary, builder_briefs = await _generate_builder_summaries(area, rows)

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(rows) < total_count,
        "builders": grouped,
        "filters": {"area": area, "tier": tier, "segment": segment},
        "area_summary": area_summary,
        "builder_briefs": builder_briefs,
    }


# ============================================================
# GET /api/builder/:slug
# ============================================================


@router.get("/builder/{slug}")
async def get_builder(slug: str, _user: dict = Depends(require_auth)):
    """Get full builder profile by slug."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM builders WHERE slug = $1 OR LOWER(name) = $1""",
            slug.lower(),
        )
        if not row:
            # Try fuzzy match
            row = await conn.fetchrow(
                """SELECT * FROM builders
                   WHERE slug LIKE '%' || $1 || '%'
                      OR LOWER(name) LIKE '%' || $1 || '%'
                   ORDER BY COALESCE(trust_score, score, 0) DESC
                   LIMIT 1""",
                slug.lower(),
            )
        if not row:
            raise HTTPException(status_code=404, detail=f"Builder '{slug}' not found")

        # Fetch builder's projects
        builder_id = row["id"]
        projects = await conn.fetch(
            """SELECT * FROM builder_projects WHERE builder_id = $1 ORDER BY status, project_name""",
            builder_id,
        )

        # Build risk flags
        risk_flags = []
        if row.get("has_nclt_proceedings"):
            risk_flags.append(
                {
                    "severity": "critical",
                    "title": "NCLT Insolvency Proceedings",
                    "detail": row.get("nclt_case_details", "Active NCLT case"),
                }
            )
        if row.get("directors_linked_to_failed"):
            risk_flags.append(
                {
                    "severity": "warning",
                    "title": "Director Network Risk",
                    "detail": row.get("director_risk_details", "Directors linked to failed/struck-off companies"),
                }
            )
        complaints = row.get("complaints", 0) or 0
        if complaints > 15:
            risk_flags.append(
                {
                    "severity": "warning",
                    "title": f"{complaints} RERA Complaints",
                    "detail": f"High complaint count ({complaints}) relative to {row.get('rera_projects', 0)} projects",
                }
            )
        if (row.get("on_time_delivery_pct") or 100) < 70:
            risk_flags.append(
                {
                    "severity": "warning",
                    "title": "Poor Delivery Record",
                    "detail": f"Only {row.get('on_time_delivery_pct')}% on-time delivery",
                }
            )
        consumer = row.get("consumer_court_cases", 0) or 0
        if consumer >= 5:
            risk_flags.append(
                {
                    "severity": "warning",
                    "title": f"{consumer} Consumer Court Cases",
                    "detail": "Multiple consumer court complaints",
                }
            )

    # Build response
    profile = dict(row)
    # Convert special types
    for key in profile:
        if isinstance(profile[key], (list,)):
            pass
        elif hasattr(profile[key], "isoformat"):
            profile[key] = profile[key].isoformat()

    profile["projects"] = [dict(p) for p in projects]
    profile["risk_flags"] = risk_flags
    if profile.get("trust_score_breakdown") and isinstance(profile["trust_score_breakdown"], str):
        profile["trust_score_breakdown"] = json.loads(profile["trust_score_breakdown"])

    return profile


# ============================================================
# GET /api/area/:slug
# ============================================================


@router.get("/area/{slug}")
async def get_area(slug: str, _user: dict = Depends(require_auth)):
    """Get area profile with builders, infrastructure, and scores."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        slug_clean = slug.lower().replace("-", " ").strip()

        # Check areas table: exact slug, then fuzzy
        area = await conn.fetchrow(
            "SELECT * FROM areas WHERE slug = $1",
            slug,
        )
        if not area:
            area = await conn.fetchrow(
                """SELECT * FROM areas
                   WHERE LOWER(name) = $1
                      OR $1 LIKE '%' || slug || '%'
                      OR slug LIKE '%' || $1 || '%'
                      OR LOWER(name) LIKE '%' || $1 || '%'
                      OR $1 LIKE '%' || LOWER(name) || '%'
                   ORDER BY LENGTH(name) DESC
                   LIMIT 1""",
                slug_clean,
            )

        # Fall back to neighborhoods table
        if not area:
            area = await conn.fetchrow(
                """SELECT id, name, name as slug,
                          ST_Y(center_geog::geometry) as latitude,
                          ST_X(center_geog::geometry) as longitude
                   FROM neighborhoods
                   WHERE LOWER(name) = $1
                      OR LOWER(name) LIKE '%' || $1 || '%'
                      OR $1 LIKE '%' || LOWER(name) || '%'
                   ORDER BY LENGTH(name) DESC
                   LIMIT 1""",
                slug_clean,
            )

        if not area:
            raise HTTPException(status_code=404, detail=f"Area '{slug}' not found")

        area_name = area.get("name", slug)

        # Find builders active in this area
        builders = await conn.fetch(
            """SELECT name, slug, trust_score, trust_tier, segment, reputation_tier,
                      rera_projects, complaints, avg_rating, active_areas
               FROM builders
               WHERE $1 = ANY(active_areas)
                  OR EXISTS (SELECT 1 FROM unnest(active_areas) a WHERE LOWER(a) LIKE '%' || $2 || '%')
               ORDER BY COALESCE(trust_score, score, 0) DESC""",
            area_name,
            slug.lower().replace("-", " "),
        )

        # Find infrastructure projects affecting this area
        infra = await conn.fetch(
            """SELECT * FROM infrastructure_projects
               WHERE $1 = ANY(affected_areas)
                  OR EXISTS (SELECT 1 FROM unnest(affected_areas) a WHERE LOWER(a) LIKE '%' || $2 || '%')""",
            area_name,
            slug.lower().replace("-", " "),
        )

        # Get property prices for area
        prices = await conn.fetchrow(
            """SELECT * FROM property_prices
               WHERE LOWER(area) LIKE '%' || $1 || '%'
               LIMIT 1""",
            slug.lower().replace("-", " "),
        )

    return {
        "area": dict(area),
        "builders": [dict(b) for b in builders],
        "infrastructure": [dict(i) for i in infra],
        "property_prices": dict(prices) if prices else None,
    }


# ============================================================
# POST /api/intelligence-brief
# ============================================================


@router.post("/intelligence-brief")
async def generate_intelligence_brief(request: IntelligenceBriefRequest, _user: dict = Depends(require_auth)):
    """Generate AI-powered intelligence brief for a property location."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service unavailable")

    from app.utils.geo import geocode_address, reverse_geocode

    lat, lon = request.latitude, request.longitude
    if not lat or not lon:
        if request.address:
            result = await geocode_address(request.address)
            if result:
                lat, lon = result
            else:
                raise HTTPException(status_code=400, detail="Could not geocode address")
        else:
            raise HTTPException(status_code=400, detail="Provide lat/lng or address")

    address = await reverse_geocode(lat, lon)
    pool = await get_pool()

    # Gather context data
    async with pool.acquire() as conn:
        # Nearby builders
        builders = await conn.fetch(
            """SELECT name, trust_score, trust_tier, rera_projects, complaints,
                      on_time_delivery_pct, avg_rating, has_nclt_proceedings
               FROM builders
               ORDER BY COALESCE(trust_score, score, 0) DESC
               LIMIT 15"""
        )

        # Nearest metro
        metro = await conn.fetchrow(
            """SELECT name, status,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as dist_km
               FROM metro_stations
               ORDER BY geog <-> ST_Point($1, $2)::geography LIMIT 1""",
            lon,
            lat,
        )

        # Property prices
        prices = await conn.fetchrow(
            """SELECT area, avg_price_sqft, yoy_growth_pct, rental_yield_pct
               FROM property_prices
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon,
            lat,
        )

        # Infrastructure
        await conn.fetch(
            "SELECT name, type, current_status, completion_percentage FROM infrastructure_projects LIMIT 5"
        )

    # Build context for Claude
    context_parts = [f"Location: {address} ({lat:.4f}, {lon:.4f})"]

    if metro:
        context_parts.append(
            f"Nearest metro: {metro['name']} ({round(float(metro['dist_km']), 1)} km, {metro['status']})"
        )

    if prices:
        context_parts.append(
            f"Property prices: ₹{prices['avg_price_sqft']}/sqft, {prices.get('yoy_growth_pct', 'N/A')}% YoY"
        )

    if builders:
        builder_lines = []
        for b in builders[:10]:
            tier = b.get("trust_tier", "unscored")
            nclt = " [NCLT!]" if b.get("has_nclt_proceedings") else ""
            builder_lines.append(
                f"  - {b['name']}: score {b.get('trust_score', 'N/A')}, tier={tier}, delivery={b.get('on_time_delivery_pct', 'N/A')}%{nclt}"
            )
        context_parts.append("Builders in area:\n" + "\n".join(builder_lines))

    if request.claims:
        context_parts.append(f"Claims to verify: {', '.join(request.claims)}")

    context = "\n".join(context_parts)

    # Call Claude
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"""You are a Bangalore real estate intelligence analyst. Based on the data below, write a 200-300 word buyer advisory brief.

Include:
1. A verdict: STRONG_BUY, BUY, CAUTION, WAIT, or AVOID
2. Key strengths of this location
3. Key risks or concerns
4. Infrastructure outlook
5. Builder landscape assessment
6. Price assessment

Be specific, data-driven, and honest. Don't sugarcoat risks.

Data:
{context}

Respond in JSON format:
{{
  "verdict": "BUY|CAUTION|etc",
  "brief": "Your 200-300 word advisory...",
  "key_strengths": ["strength1", "strength2"],
  "key_risks": ["risk1", "risk2"],
  "price_assessment": "One line on pricing"
}}""",
                        }
                    ],
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                text = data["content"][0]["text"].strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                brief = json.loads(text.strip())
                brief["address"] = address
                brief["latitude"] = lat
                brief["longitude"] = lon
                return brief

    except Exception as e:
        logger.error(f"Intelligence brief generation failed: {e}")

    raise HTTPException(status_code=500, detail="Failed to generate intelligence brief")


# ============================================================
# GET /api/infrastructure
# ============================================================


@router.get("/infrastructure")
async def list_infrastructure(
    area: str | None = Query(None),
    type: str | None = Query(None, description="metro, expressway, suburban_rail"),
    _user: dict = Depends(require_auth),
):
    """List infrastructure projects with optional area/type filters."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Try the new infrastructure_projects table first
        query = "SELECT * FROM infrastructure_projects"
        conditions = []
        params = []

        if area:
            params.append(area)
            conditions.append(f"${len(params)} = ANY(affected_areas)")
        if type:
            params.append(type)
            conditions.append(f"type = ${len(params)}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = await conn.fetch(query, *params)

        if not rows:
            # Fall back to future_infra_projects table
            query = "SELECT * FROM future_infra_projects"
            conditions = []
            params = []
            if type:
                params.append(type)
                conditions.append(f"type = ${len(params)}")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            rows = await conn.fetch(query, *params)

    return {"projects": [dict(r) for r in rows]}


# ============================================================
# GET /api/search
# ============================================================


@router.get("/search")
async def global_search(q: str = Query(..., min_length=2)):
    """Search across builders, projects, areas, and landmarks."""
    pool = await get_pool()
    results = {"builders": [], "projects": [], "areas": [], "landmarks": []}

    async with pool.acquire() as conn:
        search_term = q.lower()

        # Builders
        builders = await conn.fetch(
            """SELECT name, slug, trust_score, trust_tier, segment
               FROM builders
               WHERE LOWER(name) LIKE '%' || $1 || '%'
                  OR EXISTS (SELECT 1 FROM unnest(also_known_as) a WHERE LOWER(a) LIKE '%' || $1 || '%')
               ORDER BY COALESCE(trust_score, score, 0) DESC
               LIMIT 10""",
            search_term,
        )
        results["builders"] = [dict(b) for b in builders]

        # Projects
        projects = await conn.fetch(
            """SELECT project_name, slug, location_area, status, rera_number
               FROM builder_projects
               WHERE LOWER(project_name) LIKE '%' || $1 || '%'
                  OR LOWER(location_area) LIKE '%' || $1 || '%'
               LIMIT 10""",
            search_term,
        )
        results["projects"] = [dict(p) for p in projects]

        # Areas (from neighborhoods)
        areas = await conn.fetch(
            """SELECT name,
                      ST_Y(center_geog::geometry) as latitude,
                      ST_X(center_geog::geometry) as longitude
               FROM neighborhoods
               WHERE LOWER(name) LIKE '%' || $1 || '%'
               LIMIT 10""",
            search_term,
        )
        results["areas"] = [dict(a) for a in areas]

        # Landmarks
        landmarks = await conn.fetch(
            """SELECT name, category, latitude, longitude
               FROM landmark_registry
               WHERE LOWER(name) LIKE '%' || $1 || '%'
                  OR EXISTS (SELECT 1 FROM unnest(aliases) a WHERE LOWER(a) LIKE '%' || $1 || '%')
               LIMIT 10""",
            search_term,
        )
        results["landmarks"] = [dict(lm) for lm in landmarks]

    total = sum(len(v) for v in results.values())
    return {"query": q, "total": total, "results": results}
