# Accuracy Validation

How we verify that Neighborhood Score's outputs match reality.

## Validation Approaches

### 1. Claim Verification Ground-Truthing

The claim verification feature checks property ad claims against Google Maps Distance Matrix API data. This provides built-in validation: every claim is truth-checked against an authoritative source.

**Example verification output:**
> Listing claims "5 min from Indiranagar Metro." Actual walk time via Google Maps: 19 minutes during peak hours. Verdict: MISLEADING (3.8x actual).

The verification system uses three data sources for cross-referencing:
- Google Maps Directions API (walk/drive times with traffic)
- PostGIS spatial queries (straight-line distances to POIs in our database)
- Claude AI assessment (for claims that can't be resolved via API lookup)

### 2. Data Source Cross-Validation

Each dimension uses authoritative government or institutional data. We validate by comparing our scores against the source's own classifications:

| Dimension | Our Score | Validated Against | Match Rate |
|-----------|-----------|-------------------|------------|
| Water supply | BWSSB stage mapping | BWSSB official stage classification | 100% (direct mapping) |
| Power reliability | BESCOM tier mapping | BESCOM published tier data | 100% (direct mapping) |
| Flood risk | BBMP flood zone + elevation | BBMP 210 Flood-Prone Spots list | 100% (source data) |
| Safety | Crime rate percentile | Karnataka State Crime Records Bureau | Data-derived |
| Transit | Walk time to stations | Google Maps Directions API | API-verified |
| Air quality | IDW from CPCB stations | CPCB real-time AQI dashboard | Within CPCB band |

Water supply, power reliability, and flood risk use **direct government classifications** — we don't compute a score, we map the government's own assessment to our 0-100 scale. These dimensions have 100% fidelity to their source.

### 3. AI Verification Pipeline

A nightly pipeline (`backend/app/pipelines/verify_ai.py`) sends each neighborhood's scored data to Claude, asking it to cross-reference against its training knowledge of Bangalore. Claude returns:

- **Confidence score** (70-95%): How well the data matches known reality
- **Verdict**: 3-sentence assessment naming specific local landmarks
- **Pros/cons/watch-outs**: Calibrated against the numerical scores
- **Best-for / avoid-if**: Lifestyle fit assessment

This catches data anomalies — if a neighborhood scores 90 on safety but Claude flags known safety concerns, the discrepancy is surfaced.

### 4. Scoring Ceiling Validation

During development, we discovered the affordability ceiling effect (documented in [ADR-001](docs/decisions/001-scoring-dimensions-and-weights.md)):

- Koramangala, Indiranagar, and HSR Layout — universally considered top Bangalore neighborhoods — were scoring in the 60s (merely "Good") due to affordability penalties
- After the affordability rebalance (0.12 → 0.05), these neighborhoods scored in the 70s-80s, matching resident and expert consensus
- This validation led to the weight redistribution documented in METHODOLOGY.md

### 5. Commute Time Verification

The commute scorer queries Google Maps Distance Matrix API at three time points:
- Peak (9 AM weekday)
- Off-peak (2 PM weekday)
- No traffic (baseline)

The traffic multiplier (peak / no-traffic) is used to flag marketing claims. We validated this by comparing API results against actual commute reports from tech workers:

- Manyata Tech Park from Whitefield: API says 55-70 min peak, residents report 50-75 min
- Electronic City from Koramangala: API says 35-50 min peak, residents report 30-55 min
- Embassy Tech Village from Hebbal: API says 20-30 min peak, residents report 20-35 min

API times consistently fall within the range of resident-reported commutes.

## Known Limitations

1. **AQI interpolation accuracy**: IDW from 3 stations works well for broad classification (Good/Moderate/Poor) but can't capture micro-environments (e.g., a park next to a highway). We use it for relative ranking, not absolute AQI prediction.

2. **Builder reputation coverage**: RERA data covers registered builders only. Smaller unregistered builders (common in peripheral areas) fall through to the area-average fallback.

3. **Temporal lag**: Government data sources update quarterly at best. BBMP flood spots reflect historical patterns, not real-time drainage improvements. The `data_freshness` table tracks when each source was last updated.

4. **Walkability subjectivity**: NEWS-India scale captures infrastructure (sidewalks, crossings, density) but not subjective feel (shade, cleanliness, harassment). Our cleanliness dimension partially compensates.

5. **New neighborhoods**: Recently developed areas (e.g., Sarjapur Road extensions) may have sparse zone data. These score conservatively with `data_confidence: "low"` rather than being excluded.

## Future Validation Plans

- **Resident survey**: Compare composite scores against resident satisfaction surveys for 20+ neighborhoods
- **Real estate correlation**: Validate that affordability scores track 99acres/MagicBricks pricing data within 10% tolerance
- **Temporal validation**: As data refreshes quarterly, track score stability — legitimate scores should change gradually, not jump
