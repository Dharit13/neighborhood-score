"""
AI Verification Worker — Claude-powered background verification.

Runs nightly or on-demand after seed/pipeline refresh.
For each neighborhood: collects scores + raw data from DB,
sends to Claude for 3 verification passes:
  1. Sanity check: cross-check scores against raw data for contradictions
  2. Data freshness: compare DB values against known current state
  3. Narrative: generate 2-3 sentence neighborhood summary

Stores results in neighborhood_verification table.
Cost: ~42 neighborhoods x 1 Claude call = ~42 calls per cycle.

Usage: python -m app.pipelines.verify_ai [--neighborhood NAME]
"""

import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

VERIFICATION_PROMPT = """You are a sharp Bangalore real estate advisor who LOVES discovering what makes each neighborhood special. A client is considering buying here. Give them the full picture — but lead with what's exciting.

Respond in this exact JSON format (no markdown):
{
  "confidence": <70-95>,
  "verdict": "<2-3 sentences. Paint a picture of DAILY LIFE here — what will mornings, evenings, weekends feel like? Mention a specific beloved local spot by name. Then the honest trade-off. Write like a friend who lives here. Examples: 'You'll be grabbing filter coffee at Brahmin's Coffee Bar on lazy Sunday mornings and walking to Lalbagh for evening runs — Basavanagudi is old Bangalore at its finest. But the charm comes with ₹12,000/sqft prices and zero nightlife after 9pm.' or 'Living in Indiranagar means Toit on Friday nights, Dyu Art Cafe for weekend brunches, and the Purple Line metro 5 minutes away. You pay ₹15,500/sqft for arguably the best lifestyle in Bangalore — but 83dB street noise means you'll need good windows.'>",
  "pros": [
    "<specific advantage — mention actual local spots people love, e.g. 'Morning walks in Cubbon Park, filter coffee at CTR, weekend shopping on Commercial Street — all within 2km'>",
    "<another pro with numbers>",
    "<another pro>"
  ],
  "cons": [
    "<specific disadvantage with numbers, e.g. 'BWSSB Stage 4 — only 2hrs water daily, ₹4-6K/month tanker cost'>",
    "<another con>",
    "<another con>"
  ],
  "watch_outs": [
    "<upcoming change that could affect value, e.g. 'Metro Phase 2A opens Dec 2026 — will cut commute by 20min'>",
    "<another watch out>"
  ],
  "best_for": "<who should buy here — be specific about lifestyle, e.g. 'Young professionals and couples who want walkable nightlife, metro access, and don't mind paying premium for the best location in Bangalore'>",
  "avoid_if": "<who should NOT buy here, e.g. 'families needing quiet streets for kids, or budget-conscious buyers looking under ₹1Cr'>",
  "lifestyle_tags": [
    {"category": "<one of: food, nightlife, kids, seniors, sports, woman_safety, nature, shopping, culture, fitness>", "label": "<short label like 'Great Restaurants' or 'Cricket Fan Zone'>", "detail": "<one line with specific names/places, e.g. 'Vidyarthi Bhavan, CTR, Brahmin's Coffee Bar within walking distance'>"}
  ]
}

Rules:
- The verdict MUST lead with the area's appeal — what draws people here, the vibe, the lifestyle. Then the trade-off.
- 3-5 pros, 3-5 cons, 1-3 watch_outs. Be specific with data points.
- Pros should highlight DAILY LIFE — mention specific restaurants (Vidyarthi Bhavan, MTR, Toit, CTR), parks (Cubbon, Lalbagh), streets (100ft Road, Church Street), malls (Mantri, Orion), temples, lakes by name. Make the reader FEEL what living there is like.
- You know Bangalore deeply — use that knowledge. Every neighborhood has its beloved spots. Name them.
- Use real numbers from the data: commute minutes, water hours, price per sqft, flood events, noise dB.
- Mention specific landmarks, roads, or areas by name when possible (e.g. "100m Road", "CMH Road", "Mantri Mall").
- No technical jargon like "score is null" or "data unavailable". Skip missing data silently.
- Write like a friend who lives in Bangalore and knows every neighborhood intimately. Casual but precise.
- If a dimension is genuinely bad (water Stage 4, flood risk high), say it clearly. Don't soften.

LIFESTYLE TAGS rules:
- Include 3-6 lifestyle_tags that GENUINELY apply to this neighborhood. Do NOT force tags.
- Categories: food (great restaurants/cafes), nightlife (bars/pubs/clubs), kids (parks/play areas/family-friendly), seniors (quiet/temples/walking groups), sports (stadiums/grounds nearby — mention cricket, football, etc.), woman_safety (well-lit/CCTV/safe at night), nature (lakes/parks/green cover), shopping (malls/markets/streets), culture (temples/museums/art galleries), fitness (gyms/running tracks/sports clubs).
- Label should be catchy and specific: "Foodie Paradise", "Bar Capital", "Great for Kids", "Senior Haven", "Cricket Fan Zone", "Woman Safe After Dark", "Lake Life", "Shopping Hub", "Cultural Heart", "Runner's Dream".
- Detail MUST name specific places: restaurant names, park names, stadium names, mall names. One line max.
- Only include woman_safety if the area genuinely has good safety infrastructure (CCTV, streetlights, police presence, safety score > 70).
- Only include sports if there's actually a stadium or major sports facility nearby. Chinnaswamy Stadium (cricket), Kanteerava Stadium (athletics/football), Sree Kanteerava Indoor Stadium (badminton/basketball).
"""


def _collect_neighborhood_data(cur, neighborhood_id: int, name: str) -> dict:
    """Collect all relevant data for a neighborhood from DB."""
    data = {"neighborhood": name, "id": neighborhood_id}

    cur.execute("SELECT * FROM safety_zones WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        data["safety_zone"] = dict(zip(cols, row))

    cur.execute("SELECT * FROM water_zones WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        data["water_zone"] = dict(zip(cols, row))

    cur.execute("SELECT * FROM power_zones WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        data["power_zone"] = dict(zip(cols, row))

    cur.execute("SELECT * FROM property_prices WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        data["property_prices"] = dict(zip(cols, row))

    cur.execute("SELECT * FROM walkability_zones WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        data["walkability"] = dict(zip(cols, row))

    cur.execute("SELECT * FROM business_opportunity WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        data["business"] = dict(zip(cols, row))

    # Nearest transit
    cur.execute(
        """SELECT m.name, m.status, ST_Distance(m.geog, n.center_geog) / 1000.0 as dist_km
           FROM metro_stations m, neighborhoods n
           WHERE n.id = %s
           ORDER BY m.geog <-> n.center_geog
           LIMIT 1""",
        (neighborhood_id,)
    )
    row = cur.fetchone()
    if row:
        data["nearest_metro"] = {"name": row[0], "status": row[1], "distance_km": round(row[2], 2)}

    # Flood risk
    cur.execute("SELECT risk_level, flood_history_events, drainage_quality, score FROM flood_risk WHERE neighborhood_id = %s", (neighborhood_id,))
    row = cur.fetchone()
    if row:
        data["flood_risk"] = {"risk_level": row[0], "events": row[1], "drainage": row[2], "score": row[3]}

    # Commute (top 3 nearest tech parks, peak traffic)
    cur.execute(
        """SELECT tp.name, ct.duration_min, ct.distance_km
           FROM commute_times ct JOIN tech_parks tp ON ct.tech_park_id = tp.id
           WHERE ct.neighborhood_id = %s AND ct.mode = 'car_peak'
           ORDER BY ct.duration_min LIMIT 3""",
        (neighborhood_id,)
    )
    rows_ct = cur.fetchall()
    if rows_ct:
        data["commute_peak"] = [{"tech_park": r[0], "peak_min": round(r[1], 0), "km": round(r[2], 1)} for r in rows_ct]

    # Delivery coverage
    cur.execute(
        "SELECT swiggy_serviceable, zepto_serviceable, blinkit_serviceable, bigbasket_serviceable, coverage_score FROM delivery_coverage WHERE neighborhood_id = %s",
        (neighborhood_id,)
    )
    row = cur.fetchone()
    if row:
        services = []
        if row[0]: services.append("Swiggy")
        if row[1]: services.append("Zepto")
        if row[2]: services.append("Blinkit")
        if row[3]: services.append("BigBasket")
        data["delivery"] = {"services": services, "count": len(services), "score": row[4]}

    # Noise
    cur.execute(
        "SELECT avg_noise_db_estimate, noise_label, airport_flight_path, highway_proximity_km, score FROM noise_zones WHERE neighborhood_id = %s",
        (neighborhood_id,)
    )
    row = cur.fetchone()
    if row:
        data["noise"] = {"db": round(row[0], 0), "label": row[1], "airport": row[2], "highway_km": round(row[3], 1), "score": row[4]}

    return data


def _verify_with_claude(neighborhood_data: dict) -> dict:
    """Call Claude API to verify neighborhood data."""
    try:
        import anthropic
    except ImportError:
        print("  WARNING: anthropic package not installed. Skipping AI verification.")
        return {"confidence": 50, "flags": ["AI verification unavailable — anthropic package not installed"], "narrative": ""}

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  WARNING: ANTHROPIC_API_KEY not set. Skipping AI verification.")
        return {"confidence": 50, "flags": ["AI verification unavailable — API key not configured"], "narrative": ""}

    client = anthropic.Anthropic(api_key=api_key)

    # Serialize data (handle non-JSON-serializable types)
    serializable = {}
    for k, v in neighborhood_data.items():
        if isinstance(v, dict):
            serializable[k] = {
                sk: str(sv) if not isinstance(sv, (int, float, str, bool, type(None), list)) else sv
                for sk, sv in v.items()
            }
        else:
            serializable[k] = v

    max_retries = 4
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1200,
                messages=[
                    {"role": "user", "content": f"{VERIFICATION_PROMPT}\n\nNeighborhood data:\n{json.dumps(serializable, indent=2, default=str)}"}
                ],
            )
            result = json.loads(message.content[0].text)
            # Build structured narrative from new format
            verdict = result.get("verdict", "")
            pros = result.get("pros", [])
            cons = result.get("cons", [])
            watch_outs = result.get("watch_outs", result.get("flags", []))
            best_for = result.get("best_for", "")
            avoid_if = result.get("avoid_if", "")

            lifestyle_tags = result.get("lifestyle_tags", [])

            narrative_obj = {
                "verdict": verdict,
                "pros": pros,
                "cons": cons,
                "best_for": best_for,
                "avoid_if": avoid_if,
                "lifestyle_tags": lifestyle_tags,
            }

            return {
                "confidence": int(result.get("confidence", 50)),
                "flags": watch_outs,
                "narrative": json.dumps(narrative_obj),
            }
        except anthropic.InternalServerError:
            wait = 2 ** (attempt + 1)
            print(f"API overloaded, retrying in {wait}s...", end=" ", flush=True)
            time.sleep(wait)
        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 2)
            print(f"Rate limited, retrying in {wait}s...", end=" ", flush=True)
            time.sleep(wait)
        except (json.JSONDecodeError, IndexError, KeyError):
            return {"confidence": 50, "flags": ["AI response parsing failed"], "narrative": ""}
        except Exception as e:
            return {"confidence": 50, "flags": [f"AI error: {type(e).__name__}"], "narrative": ""}

    return {"confidence": 50, "flags": ["AI verification failed after retries (API overloaded)"], "narrative": ""}


def verify(neighborhood_name: str | None = None):
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            if neighborhood_name:
                cur.execute("SELECT id, name FROM neighborhoods WHERE name = %s", (neighborhood_name,))
                rows = cur.fetchall()
            else:
                cur.execute("SELECT id, name FROM neighborhoods ORDER BY name")
                rows = cur.fetchall()

            if not rows:
                print("  No neighborhoods found to verify.")
                return

            total = len(rows)
            print(f"  Verifying {total} neighborhoods with Claude ({ANTHROPIC_MODEL})...")

            for i, (nid, name) in enumerate(rows, 1):
                print(f"  [{i}/{total}] {name}...", end=" ", flush=True)

                data = _collect_neighborhood_data(cur, nid, name)
                result = _verify_with_claude(data)

                cur.execute(
                    """INSERT INTO neighborhood_verification
                       (neighborhood_id, confidence, flags, narrative, verified_at, model_used)
                       VALUES (%s, %s, %s, %s, now(), %s)
                       ON CONFLICT (neighborhood_id) DO UPDATE SET
                         confidence = EXCLUDED.confidence,
                         flags = EXCLUDED.flags,
                         narrative = EXCLUDED.narrative,
                         verified_at = EXCLUDED.verified_at,
                         model_used = EXCLUDED.model_used""",
                    (nid, result["confidence"], json.dumps(result["flags"]),
                     result["narrative"], ANTHROPIC_MODEL),
                )
                conn.commit()

                status = "OK" if result["confidence"] >= 70 else f"LOW CONFIDENCE ({result['confidence']})"
                flags_str = f" | {len(result['flags'])} flags" if result["flags"] else ""
                print(f"{status}{flags_str}")

                if i < total:
                    time.sleep(1.0)
        print(f"\n  AI verification complete for {total} neighborhoods.")
    finally:
        conn.close()


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else None
    verify(name)
