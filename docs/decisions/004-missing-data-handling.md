# ADR-004: Missing Data Handling Strategy

**Status:** Accepted
**Date:** 2025-12-10

## Context

Not all 130+ neighborhoods have complete data across all 17 dimensions. Some neighborhoods lack safety zone records, others have no BWSSB water classification, and newer areas may have sparse POI data. We needed a strategy for computing scores when data is incomplete.

Three approaches were considered:

1. **Interpolation** — Estimate missing scores from neighboring areas
2. **Exclusion** — Skip the dimension and re-normalize remaining weights
3. **Conservative defaults** — Assign a neutral-to-low score with a confidence flag

## Decision

We chose **conservative defaults with explicit confidence signaling**.

### How It Works

When a scorer finds no data for a neighborhood, it returns a `ScoreResult` with:

- **A neutral-to-conservative default score** (40–70 depending on dimension)
- **`data_confidence: "low"`** flag
- **`breakdown.note`** explaining the data gap
- **Named sources** documenting what was looked for and not found

Each dimension has a specific default based on the risk profile:

| Dimension | Default Score | Rationale |
|-----------|--------------|-----------|
| Safety | 50.0 | Neutral — absence of crime data ≠ safe |
| Flood risk | 70.0 | No BBMP flood data = likely not a known flood zone |
| Water supply | 30.0 | Conservative — defaults to Stage 5 (worst) |
| Air quality | 50.0 | City median assumption |
| Noise | 60.0 | Neutral-to-quiet assumption |
| Power reliability | 50.0 | Mid-tier assumption |
| Walkability | 40.0 | Below average — most Bangalore areas lack walkability |
| Future infrastructure | 20.0 | No planned projects = low opportunity signal |
| Business opportunity | 40.0 | Below average default |
| Delivery coverage | Formula-based | `(services/4) * 80 + time_bonus` |

### Why Not Interpolation?

Bangalore neighborhoods are spatially heterogeneous. Koramangala (safe, walkable) is 2km from Ejipura (flood-prone, different safety profile). Spatial interpolation would produce misleading averages. The data boundaries are administrative (BBMP wards, BWSSB zones, BESCOM divisions), not gradients — interpolation across these boundaries is statistically unsound.

### Why Not Exclusion?

Re-normalizing weights when a dimension is missing changes the composite formula per-neighborhood, making scores incomparable. A neighborhood missing flood data would have its other dimensions inflated, potentially ranking higher than one with complete data.

## Consequences

- Scores are always comparable — same 17-dimension formula for every neighborhood
- Users see `data_confidence: "low"` in the API response; frontend can show uncertainty indicators
- Conservative defaults mean neighborhoods with missing data tend to score lower — this is intentional (unknown ≠ good)
- Water supply defaults to worst-case (Stage 5) because "no BWSSB data" in Bangalore typically means peripheral areas with tanker dependency
- As data coverage improves, defaults are replaced with real scores automatically (zone records override defaults)
