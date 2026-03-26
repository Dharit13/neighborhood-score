"""
Claude-based claim parser for property ad claims.

Replaces brittle regex approach with LLM structured extraction.
Parses varied ad copy like:
  - "5 min from metro"
  - "20 min to Electronic City"
  - "near Silk Board"
  - "walking distance to school"
  - "2 km from airport"
  - "right next to ORR"
  - "close to upcoming metro station"

Also handles free-form marketing paragraphs by splitting them into
individual atomic claims before parsing.
"""

import os
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

SPLIT_PROMPT = """You are a Bangalore real estate marketing text analyzer. Your job is to take raw marketing copy — which may be a paragraph, multiple sentences, or bullet points — and split it into individual, atomic location/distance/proximity claims.

VALIDATION — check these FIRST before splitting:
1. The text must be about a property in Bangalore or Greater Bangalore (includes Whitefield, Sarjapur, Electronic City, Devanahalli, Hosur Road, Yelahanka, Kanakapura, Tumkur Road, Hennur, etc.). If the property is clearly in another city (Mumbai, Delhi, Chennai, Hyderabad, etc.), return: {"error": "This tool only works for properties in Bangalore and Greater Bangalore area."}
2. The text must contain real estate marketing claims about proximity, distance, connectivity, or nearby amenities. If the text is gibberish, completely unrelated (e.g., recipes, code, random text), or contains no location/proximity claims at all, return: {"error": "Please paste property marketing text containing location or connectivity claims (e.g., '5 min from metro', 'near schools')."}
3. If the text is valid, proceed with splitting below.

Splitting rules:
- Each output claim should reference EXACTLY ONE destination/landmark.
- Preserve the original phrasing as closely as possible, but make each claim self-contained.
- If a sentence says "15 minutes from ITPL, Outer Ring Road and Sarjapur Road", split into 3 separate claims: one for ITPL, one for Outer Ring Road, one for Sarjapur Road — each keeping the "15 minutes" context.
- If a sentence says "a few minutes from X and Y", split into 2 claims with the same time qualifier.
- Ignore non-location claims (e.g., "luxury amenities", "world-class clubhouse", "RERA approved") — only extract claims about proximity, distance, or travel time to places.
- DO keep claims about nearby amenity categories like "close to schools", "near hospitals", "close to colleges", "healthcare centres nearby", "essential amenities" — these ARE location/proximity claims even though they don't name a specific place.
- If the text mentions "upcoming" or "proposed" infrastructure, still include it as a claim.
- Keep the original tone/qualifier (e.g., "a few minutes", "about 15 minutes", "just 5 min").

Examples:

Input: "It is a few minutes from a Purple Line Metro Station and the upcoming Blue Line Metro Station, and is about 15 minutes from ITPL, Outer Ring Road and Sarjapur Road."

Output:
["A few minutes from a Purple Line Metro Station", "A few minutes from the upcoming Blue Line Metro Station", "About 15 minutes from ITPL", "About 15 minutes from Outer Ring Road", "About 15 minutes from Sarjapur Road"]

Input: "Located just 2 km from the airport and walking distance to Indiranagar metro. The project is near Koramangala and 30 min drive to Electronic City."

Output:
["2 km from the airport", "Walking distance to Indiranagar metro", "Near Koramangala", "30 min drive to Electronic City"]

Input: "5 min from metro"

Output:
["5 min from metro"]

Input: "Best pizza places in Mumbai near Andheri station"

Output:
{"error": "This tool only works for properties in Bangalore and Greater Bangalore area."}

Input: "hello world test 123 asdf"

Output:
{"error": "Please paste property marketing text containing location or connectivity claims (e.g., '5 min from metro', 'near schools')."}

Respond with ONLY a JSON array of strings OR an error object. No markdown, no explanation."""


async def split_claims_text(raw_text: str) -> list[str]:
    """Split free-form marketing text into individual atomic claims using Claude."""
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.strip().split('\n') if line.strip()]

    looks_atomic = all(
        len(line.split()) <= 10
        and (',' not in line or line.count(',') <= 1)
        and ' and ' not in line.lower()
        for line in lines
    )
    if looks_atomic and len(lines) >= 1:
        return lines

    if not ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY — returning raw lines as claims")
        return lines

    try:
        import httpx
        combined = "\n".join(lines)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{SPLIT_PROMPT}\n\nMarketing text to split:\n{combined}",
                        }
                    ],
                },
            )

            if resp.status_code != 200:
                logger.warning(f"Claude split API error {resp.status_code}: {resp.text[:200]}")
                return lines

            data = resp.json()
            text = data["content"][0]["text"].strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            parsed = json.loads(text)

            if isinstance(parsed, dict) and "error" in parsed:
                raise ValueError(parsed["error"])

            if isinstance(parsed, list) and len(parsed) >= 1:
                return [str(c) for c in parsed if str(c).strip()]

            logger.warning(f"Claude split returned unexpected format: {type(parsed)}")
            return lines

    except Exception as e:
        logger.warning(f"Claude claim splitting failed: {e}")
        return lines


AI_VERIFY_PROMPT = """You are a Bangalore real estate fact-checker with access to real neighborhood data. Given a property address, actual neighborhood data from our database, and claims that could not be verified through database lookups, verify them using the provided data as your PRIMARY source, supplemented by your knowledge of Bangalore.

For each claim, respond with a JSON object containing:
- "original_claim": the claim text
- "verdict": one of "ACCURATE", "SLIGHTLY_MISLEADING", "MISLEADING", or "UNVERIFIABLE"
- "explanation": a concise 1-2 sentence explanation with specific details. Reference the actual data provided (e.g., name the specific schools/hospitals from the data, cite safety scores, mention exact distances).
- "actual_value": what the reality is based on the data (e.g., "3 NABH hospitals within 3km: Manipal (1.2km), Fortis (2.1km), Apollo (2.8km)")
- "claimed_value": what was claimed (e.g., "close to hospitals")

IMPORTANT:
- The NEIGHBORHOOD DATA section contains real, verified data from our database. Use it as ground truth.
- For school/hospital claims, use the nearby_schools and nearby_hospitals data — name the actual institutions and their distances.
- For safety claims, use the safety data (crime rate, CCTV density, police density).
- For price claims, use property_prices data.
- For connectivity claims, use key_distances data (airport, Majestic, railway station times with/without traffic).
- For water/power claims, use the water_supply and power_supply data.
- Only use "UNVERIFIABLE" if neither the data nor your knowledge can verify the claim.
- Be specific — cite real numbers and place names from the data provided.

Respond with ONLY a JSON array of objects. No markdown, no explanation."""


async def verify_claims_via_ai(
    address: str,
    lat: float,
    lon: float,
    unresolved_claims: list[str],
    locality_data: Optional[dict] = None,
) -> list[dict]:
    """Use AI to verify claims that couldn't be resolved through the database."""
    if not ANTHROPIC_API_KEY or not unresolved_claims:
        return []

    try:
        import httpx
        context = f"Property location: {address} (lat: {lat}, lon: {lon})\n\n"
        if locality_data:
            context += "NEIGHBORHOOD DATA (use as ground truth):\n"
            context += json.dumps(locality_data, indent=2, default=str)
            context += "\n\n"
        context += "Claims to verify:\n"
        context += json.dumps(unresolved_claims)

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 800,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{AI_VERIFY_PROMPT}\n\n{context}",
                        }
                    ],
                },
            )

            if resp.status_code != 200:
                logger.warning(f"Claude AI verify error {resp.status_code}")
                return []

            data = resp.json()
            text = data["content"][0]["text"].strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
            return []

    except Exception as e:
        logger.warning(f"Claude AI claim verification failed: {e}")
        return []


NARRATIVE_PROMPT = """You are a sharp, no-nonsense real estate analyst helping home buyers in Bangalore cut through marketing spin.

Given structured claim verification results AND real neighborhood data for a property, write a clear, conversational analysis. Be direct and useful.

Guidelines:
- Write in 2nd person ("you", "your commute") — you're talking to a buyer.
- Lead with the bottom line: is this listing honest or spinning the truth?
- For each claim, explain what was claimed vs what's actually true, in plain language. Use actual numbers.
- Group related claims naturally (e.g., metro claims together, road connectivity together).
- Call out misleading claims firmly but not aggressively. Use phrases like "in reality", "what they don't mention", "during peak hours".
- Acknowledge accurate claims — give credit where due.
- For "a few minutes" type vague claims, note that the vagueness itself is a tactic.
- Mention peak vs off-peak differences when significant.
- If you can identify the builder/developer from the property name (e.g., "Prestige" from "Prestige Somerville"), add ONE sentence about the builder's reputation — is it a plus point, a red flag, or neutral? Be specific and honest (e.g., "Prestige is one of Bangalore's most established developers with a strong delivery track record, which is a plus."). Only add this if you actually know the builder.
- IMPORTANT: You have real NEIGHBORHOOD DATA from our database. Use it to enrich your narrative:
  - If nearby_schools data is provided, mention specific school names and distances when relevant.
  - If nearby_hospitals data is provided, mention specific hospital names, accreditation, and distances.
  - If key_distances data is provided (airport, Majestic, railway station), mention these travel times with peak/off-peak distinction — even if the listing didn't claim them. Buyers always want to know.
  - If safety data shows notable crime rates or good CCTV coverage, mention it.
  - If property_prices data is available, you can reference the area's price range for context.
  - If water_supply or power_supply data reveals issues (e.g., Stage 4 water, frequent outages), flag it as something the listing doesn't mention.
- End with a 1-2 sentence practical takeaway for the buyer.
- Keep it concise — aim for 200-400 words total. No bullet points, no headers, no markdown formatting. Just flowing paragraphs.
- Do NOT repeat the raw numbers mechanically (e.g., don't say "claimed 5 min actual 19 min gap 14 min"). Weave the data into natural sentences.

Example tone:
"The listing says this property is 5 minutes from a metro station. In reality, the nearest Purple Line station is about 19 minutes away during peak traffic — nearly 4x what's advertised. That's not a rounding error, that's a different commute entirely. On the plus side, you've got Manipal Hospital just 1.2 km away and two CBSE-ranked schools within 3 km — the area's genuinely family-friendly."

Respond with ONLY the narrative text. No JSON, no markdown."""


async def generate_claim_narrative(
    address: str,
    verifications: list[dict],
    summary: str,
    locality_data: Optional[dict] = None,
) -> str:
    """Generate a readable narrative analysis of claim verification results."""
    if not ANTHROPIC_API_KEY or not verifications:
        return _fallback_narrative(verifications, summary)

    context_lines = []
    for v in verifications:
        d = v.get("details", {})
        line = f"Claim: \"{v['original_claim']}\"\n"
        line += f"  Verdict: {v['verdict']}\n"
        line += f"  Claimed: {v['claimed_value']}, Actual: {v['actual_value']}, Gap: {v['difference']}\n"
        if d.get("destination"):
            line += f"  Destination resolved to: {d['destination']} ({d.get('destination_category', 'unknown')})\n"
        if d.get("peak_duration_min") is not None:
            line += f"  Peak: {d['peak_duration_min']} min, Off-peak: {d.get('offpeak_duration_min', '?')} min\n"
        if d.get("road_distance_km") is not None:
            line += f"  Road distance: {d['road_distance_km']} km, Straight line: {d.get('straight_line_km', '?')} km\n"
        if d.get("explanation"):
            line += f"  Note: {d['explanation']}\n"
        context_lines.append(line)

    context = f"Property: {address}\nOverall: {summary}\n\n"
    if locality_data:
        context += "NEIGHBORHOOD DATA (real data from our database — use to enrich your narrative):\n"
        context += json.dumps(locality_data, indent=2, default=str)
        context += "\n\n"
    context += "\n".join(context_lines)

    try:
        import httpx
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{NARRATIVE_PROMPT}\n\nVerification results:\n{context}",
                        }
                    ],
                },
            )

            if resp.status_code != 200:
                logger.warning(f"Claude narrative API error {resp.status_code}")
                return _fallback_narrative(verifications, summary)

            data = resp.json()
            return data["content"][0]["text"].strip()

    except Exception as e:
        logger.warning(f"Claude narrative generation failed: {e}")
        return _fallback_narrative(verifications, summary)


def _fallback_narrative(verifications: list[dict], summary: str) -> str:
    """Simple fallback when AI is unavailable."""
    parts = [summary + "\n"]
    for v in verifications:
        d = v.get("details", {})
        explanation = d.get("explanation", "")
        if explanation:
            parts.append(f'"{v["original_claim"]}" — {explanation}')
        else:
            parts.append(f'"{v["original_claim"]}" — {v["verdict"].replace("_", " ").lower()}.')
    return "\n\n".join(parts)


PARSE_PROMPT = """You are a Bangalore real estate claim parser. Extract structured data from property advertisement claims.

For each claim, extract:
- destination: The place/landmark being referenced (e.g., "metro", "Electronic City", "airport", "Silk Board", "school"). Use the most specific name possible.
- claimed_value: The numeric value claimed (e.g., 5, 20, 2.5). If no specific number, use null.
- claimed_unit: The unit ("min", "km", "m", "hours"). If no unit specified, infer from context.
- travel_mode: How they're implying travel ("walk", "drive", "transit", "unspecified"). "near" or "close to" = unspecified. "walking distance" = walk.
- destination_type: What kind of place ("metro_station", "tech_park", "junction", "area", "airport", "hospital", "school", "mall", "railway_station", "bus_terminal", "generic")
- is_proximity_claim: true if the claim is vague like "near", "close to", "adjacent to" without a specific distance/time

Bangalore context:
- "ORR" = Outer Ring Road
- "EC" or "E-City" = Electronic City
- "Silk Board" = Silk Board Junction
- "Majestic" = Majestic/Kempegowda Bus Station area
- "ITPL" = International Tech Park Whitefield
- "metro" without qualifier = nearest metro station (destination: "metro")
- "Purple Line Metro Station" = destination: "Purple Line Metro", destination_type: "metro_station"
- "Blue Line Metro" = destination: "Blue Line Metro", destination_type: "metro_station"
- "Yellow Line" / "Pink Line" / "Green Line" = same pattern, use line color + "Line Metro"
- "upcoming metro" / "upcoming Blue Line" = still resolve as metro_station, the system knows which are under construction
- "airport" = Kempegowda International Airport
- IMPORTANT: Never set destination to null if a place is mentioned. Even vague references like "metro station" should have destination: "metro". Only set null if the claim has no place reference at all.

Respond with a JSON array. One object per claim. Example:

Input claims: ["5 min walk from metro", "20 min to Electronic City", "near Silk Board"]

Output:
[
  {"destination": "metro", "claimed_value": 5, "claimed_unit": "min", "travel_mode": "walk", "destination_type": "metro_station", "is_proximity_claim": false},
  {"destination": "Electronic City", "claimed_value": 20, "claimed_unit": "min", "travel_mode": "drive", "destination_type": "tech_park", "is_proximity_claim": false},
  {"destination": "Silk Board Junction", "claimed_value": null, "claimed_unit": null, "travel_mode": "unspecified", "destination_type": "junction", "is_proximity_claim": true}
]

ONLY output the JSON array. No markdown, no explanation."""


async def parse_claims(claims: list[str]) -> list[dict]:
    """Parse property ad claims using Claude structured outputs."""
    if not ANTHROPIC_API_KEY:
        logger.warning("No ANTHROPIC_API_KEY — falling back to regex parsing")
        return _regex_fallback(claims)

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{PARSE_PROMPT}\n\nClaims to parse:\n{json.dumps(claims)}",
                        }
                    ],
                },
            )

            if resp.status_code != 200:
                logger.warning(f"Claude API error {resp.status_code}: {resp.text[:200]}")
                return _regex_fallback(claims)

            data = resp.json()
            text = data["content"][0]["text"].strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) == len(claims):
                return parsed

            logger.warning(f"Claude returned {len(parsed)} results for {len(claims)} claims")
            return _regex_fallback(claims)

    except Exception as e:
        logger.warning(f"Claude claim parsing failed: {e}")
        return _regex_fallback(claims)


def _regex_fallback(claims: list[str]) -> list[dict]:
    """Fallback regex parser when Claude is unavailable."""
    import re
    results = []
    for claim in claims:
        cl = claim.lower().strip()
        parsed: dict[str, Any] = {
            "destination": None,
            "claimed_value": None,
            "claimed_unit": None,
            "travel_mode": "unspecified",
            "destination_type": "generic",
            "is_proximity_claim": False,
        }

        # "X min walk/drive to/from Y"
        m = re.search(r'(\d+)\s*min\w*\s*(?:walk\w*\s*)?(?:from|to)\s+(?:the\s+)?(?:nearest\s+)?(.+)', cl)
        if m:
            parsed["claimed_value"] = int(m.group(1))
            parsed["claimed_unit"] = "min"
            dest = m.group(2).strip().rstrip('.')
            parsed["destination"] = dest
            if "walk" in cl:
                parsed["travel_mode"] = "walk"
            elif "drive" in cl or "driv" in cl:
                parsed["travel_mode"] = "drive"
            if "metro" in dest:
                parsed["destination_type"] = "metro_station"
            elif any(k in dest for k in ["airport", "kia", "bial"]):
                parsed["destination_type"] = "airport"
            results.append(parsed)
            continue

        # "X km from/to Y"
        m = re.search(r'(\d+(?:\.\d+)?)\s*km\s*(?:from|to|near)\s+(.+)', cl)
        if m:
            parsed["claimed_value"] = float(m.group(1))
            parsed["claimed_unit"] = "km"
            parsed["destination"] = m.group(2).strip().rstrip('.')
            results.append(parsed)
            continue

        # "near X" / "close to X"
        m = re.search(r'(?:near|close\s+to|adjacent\s+to|next\s+to)\s+(.+)', cl)
        if m:
            parsed["destination"] = m.group(1).strip().rstrip('.')
            parsed["is_proximity_claim"] = True
            results.append(parsed)
            continue

        # "walking distance to X"
        m = re.search(r'walk\w*\s+distance\s+(?:to|from)\s+(.+)', cl)
        if m:
            parsed["destination"] = m.group(1).strip().rstrip('.')
            parsed["travel_mode"] = "walk"
            parsed["is_proximity_claim"] = True
            results.append(parsed)
            continue

        # Unmatched
        results.append(parsed)

    return results
