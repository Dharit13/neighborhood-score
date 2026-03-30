# ADR-001: Scoring Dimensions and Weight Selection

**Status:** Accepted
**Date:** 2025-12-15 (initial), 2026-02-20 (affordability rebalance)

## Context

We needed a composite livability score for 130+ Bangalore neighborhoods. The challenge: which dimensions to include, and how much each should contribute to the final score.

Arbitrary weighting ("safety feels important, give it 20%") produces scores that don't match buyer priorities. We needed an evidence-based starting point.

## Decision

### Dimension Selection (17 dimensions)

We selected dimensions based on three criteria:

1. **Buyer survey data** — ANAROCK Homebuyer Sentiment Survey H1 2025 identified top buyer priorities post-COVID: safety (43%), price/affordability (49%), amenities (38%), commute (14%), school access (6%).

2. **Bangalore-specific pain points** — BuildWatch Bangalore 2025 flagged flooding as the #1 buyer concern. BWSSB's ongoing water scarcity crisis and ORR/tech corridor commute pain added water supply and commute as elevated dimensions.

3. **Data availability** — Each dimension requires authoritative, regularly updated data. We only included dimensions where we had a credible government or institutional data source (see ADR-004 for missing data handling).

### Weight Derivation

Starting weights were mapped from ANAROCK H1 2025 survey percentages, normalized to 1.0 across 17 dimensions. Bangalore-specific adjustments:

| Dimension | Weight | Source / Rationale |
|-----------|--------|-------------------|
| Safety | 0.14 | ANAROCK 43% priority, +0.02 rebalance |
| Transit | 0.09 | MOHUA TOD Policy norms |
| Walkability | 0.09 | NEWS-India scale (Sallis et al. 2016), +0.02 rebalance |
| Flood risk | 0.08 | BuildWatch 2025 — #1 Bangalore concern |
| Commute | 0.08 | ORR/tech corridor pain point |
| Air quality | 0.08 | CPCB monitoring, +0.02 rebalance |
| Hospital access | 0.07 | IPHS 2022 norms (1 bed/1000 pop) |
| Water supply | 0.07 | BWSSB scarcity crisis |
| School access | 0.06 | RTE Act Section 6, +0.01 rebalance |
| Affordability | 0.05 | Reduced from 0.12 (see below) |
| Noise | 0.04 | CPCB noise monitoring |
| Power reliability | 0.04 | BESCOM tier classification |
| Future infra | 0.04 | MOHUA TOD proximity |
| Cleanliness | 0.03 | Slum proximity + BBMP waste data |
| Builder reputation | 0.03 | RERA compliance tracking |
| Delivery coverage | 0.005 | Convenience signal, not livability driver |
| Business opportunity | 0.005 | Niche signal for entrepreneurs |

### Affordability Rebalance (February 2026)

Original affordability weight was 0.12 (matching ANAROCK's 49% price priority). Problem: premium neighborhoods (Koramangala, Indiranagar) scored <10 on affordability, creating a ~12-point ceiling that made "Very Good" (75+) mathematically unreachable for objectively excellent neighborhoods.

Resolution: Reduced affordability to 0.05, redistributed 0.07 to safety (+0.02), walkability (+0.02), air quality (+0.02), school access (+0.01). Affordability is still displayed as a dimension card — buyers see the data — but it no longer dominates the composite.

## Consequences

- Composite scores align with buyer priorities as measured by ANAROCK survey data
- Bangalore-specific concerns (flooding, water, commute) are appropriately elevated
- Premium neighborhoods are no longer artificially capped by affordability penalty
- Weights are transparent and documented — users can see exactly why a score is what it is
- Delivery/business are included at 0.5% each as signals, not as livability drivers
