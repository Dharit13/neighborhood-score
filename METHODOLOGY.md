# Scoring Methodology

How Neighborhood Score computes livability scores for 126 Bangalore neighborhoods across 17 dimensions.

## Weight Selection Process

### Step 1: Buyer Priority Baseline

We started with the **ANAROCK Homebuyer Sentiment Survey H1 2025**, the largest Indian homebuyer survey (10,000+ respondents). Post-COVID priority shifts:

| ANAROCK Priority | Survey % | Our Mapping |
|-----------------|----------|-------------|
| Safety & security | 43% | safety (0.14) |
| Price & affordability | 49% | affordability (0.05, reduced — see below) |
| Amenities & infrastructure | 38% | hospital, school, water, power, walkability |
| Commute & connectivity | 14% | transit, commute |
| Educational institutions | 6% | school_access |

### Step 2: Bangalore-Specific Adjustments

National survey data doesn't capture Bangalore's unique pain points. We elevated three dimensions based on local evidence:

- **Flood risk → 0.08**: BuildWatch Bangalore 2025 identified flooding as the #1 buyer concern. BBMP's 210 flood-prone spot list and the 2024 ORR flooding validated this.
- **Water supply → 0.07**: BWSSB's Cauvery water allocation crisis (2024-2025) made water availability a deal-breaker for many neighborhoods. Stage 1 vs Stage 5 classification has direct quality-of-life impact.
- **Commute → 0.08**: Bangalore's ORR/tech corridor congestion is uniquely severe. Google Maps data shows 2-4x traffic multipliers during peak hours on key routes.

### Step 3: Affordability Rebalance

Original affordability weight was 0.12 (proportional to ANAROCK's 49% price priority). During validation, we discovered a ceiling effect: premium neighborhoods like Koramangala and Indiranagar scored <10/100 on affordability, creating a ~12-point drag that made composite scores above 75 ("Very Good") mathematically unreachable for objectively excellent neighborhoods.

Resolution: Affordability reduced to 0.05. The 0.07 difference was redistributed to safety (+0.02), walkability (+0.02), air quality (+0.02), and school access (+0.01). Affordability data is still displayed as a full dimension card — buyers see the price picture — but it no longer dominates the composite.

### Step 4: Micro-Dimensions

Two dimensions are weighted at 0.5% each as convenience signals rather than livability drivers:

- **Delivery coverage (0.005)**: Quick commerce availability (Zepto, Blinkit, Swiggy Instamart, BigBasket) — relevant to lifestyle but not a livability fundamental.
- **Business opportunity (0.005)**: Startup ecosystem, coworking density, commercial activity — niche signal for entrepreneurs.

## Scoring Models by Dimension

### Safety (14%)
**Sources:** MOHUA Ease of Living Index, NARI 2025 (women's safety), Karnataka Crime Data (NCRB), BBMP streetlight data, police station locations (data.opencity.in)

**Formula:** Equal-weighted composite per MOHUA methodology:
- 25% CCTV density per sq km
- 25% Crime rate (inverted percentile — lower crime = higher score)
- 25% Streetlight coverage %
- 25% Police station accessibility (distance-based)

### Transit Access (9%)
**Sources:** MOHUA TOD Policy 2017, BMTC bus stops (openbangalore), Namma Metro stations (data.opencity.in), South Western Railway, Google Maps Directions API

**Formula:** Modal-weighted transit score:
- 35% Metro proximity (500m optimal, 800m acceptable per MOHUA TOD)
- 30% Bus stop density and proximity
- 20% Train station access
- 15% Multi-modal bonus (presence of 2+ transit modes within walkable distance)

Walk times verified via Google Maps Directions API; OpenRouteService as fallback.

### Walkability (9%)
**Sources:** NEWS-India scale (Sallis et al. 2016, MDPI Int. J. Environ. Res. Public Health), OpenStreetMap Overpass API, Bengaluru Walkability Datajam 2023 (opencity.in)

Pre-computed zone scores based on NEWS-India methodology: residential density, land-use mix, street connectivity, pedestrian infrastructure, aesthetics, safety from traffic. Green space bonus for parks within 1km.

### Flood Risk (8%)
**Sources:** BBMP 210 Flood-Prone Spots (data.opencity.in), KSNDMC elevation data, Google Elevation API, KC Valley/Hebbal valley mapping

**Scoring:** Inverted — 100 = safest (no flood risk), 0 = severe flood zone. Based on BBMP ward classification, elevation data, and historical flooding records.

### Commute (8%)
**Sources:** Google Maps Distance Matrix API (peak 9 AM, off-peak 2 PM, baseline no-traffic), tech park locations with employee counts (Manyata, Embassy, ITPL, Electronic City)

**Formula:** Weighted average of commute times to 3 nearest tech parks, weighted by employee count. Traffic multiplier detection flags marketing lies (e.g., "20 min to Electronic City" that's actually 55 min in peak traffic).

### Air Quality (8%)
**Sources:** CPCB AQI monitoring stations, PM2.5 breakpoints (0-30 Good → 250+ Severe)

**Method:** Inverse-distance weighted (IDW) interpolation across 3 nearest CPCB monitoring stations. Weight = 1/max(distance_km, 0.1). This handles Bangalore's spatial AQI variation (industrial zones vs parks) better than nearest-station assignment.

Reference: Nature Scientific Reports (doi:10.1038/s41598-025-00814-9) for AQI spatial analysis methodology.

### Hospital Access (7%)
**Sources:** IPHS 2022 (Indian Public Health Standards), NABH accreditation database (portal.nabh.co), BBMP hospital list (data.opencity.in)

**Formula:**
- 50% NABH-accredited hospital proximity
- 30% Bed density (IPHS benchmark: 1 bed per 1,000 population)
- 20% Emergency access (distance to nearest emergency department)

### Water Supply (7%)
**Sources:** BWSSB Stage-wise Cauvery water classification, Bengaluru Water Tanker Survey 2025

**Method:** Direct BWSSB stage mapping — not a computed score. Stage 1 (full Cauvery supply, 4+ hrs/day) → 80+ score. Stage 5 (tanker-dependent) → 20 score. This uses the water utility's own classification rather than applying our own formula.

### School Access (6%)
**Sources:** RTE Act Section 6 (1km primary, 3km upper primary), Times Now/IIRF Rankings 2024, SchoolMyKids fee data, Google Places

**Formula:**
- 30% RTE distance compliance
- 25% Quality school proximity (ranked schools within 3km)
- 15% Board diversity (CBSE, ICSE, State, IB presence)
- 15% Admission accessibility
- 15% Fee affordability

### Affordability (5%)
**Sources:** RBI Residential Asset Price Monitoring, ANAROCK H1 2025, 99acres/MagicBricks pricing

**Formula:** EMI-to-income ratio at SBI/HDFC benchmark (8% p.a., 20-year tenure, Rs.836/lakh/month):
- <30% EMI/income → 80-100 (Comfortable)
- 30-40% → 60-80 (Manageable)
- 40-50% → 40-60 (Stretched)
- 50-70% → 20-40 (Severely stretched)
- >70% → 0-20 (Severely unaffordable)

### Noise (4%)
**Sources:** CPCB noise monitoring (dB Leq), DGCA/BIAL KIA flight approach data (64-70 dB), HAL Airport flight path (The Hindu Apr 2025), highway proximity (NH44, NH75, ORR, NICE)

### Power Reliability (4%)
**Sources:** BESCOM tier classification, NetZero India tracker, underground cabling data (29 localities)

**Method:** Direct BESCOM tier mapping:
- Tier 1 (2-4 outage hrs/month) → 85
- Tier 2 (6-8 hrs) → 70
- Tier 3 (10-12 hrs) → 50
- Tier 4 (14-16 hrs) → 25

### Future Infrastructure (4%)
**Sources:** MOHUA TOD norms, Metro Phase 2A/2B tracker, Bengaluru Suburban Railway project, Business Corridor (Rs.27,000 Cr project)

Proximity to planned infrastructure within 500m (optimal) / 800m (acceptable) per MOHUA TOD Policy.

### Cleanliness (3%)
**Sources:** Bengaluru Slums Map (CNN satellite, DN deprivation index 0-245), BBMP dry waste centres (336 locations), BBMP landfills (3), BBMP waste processing + biomethanisation plants (data.opencity.in)

**Formula:**
- 40% Slum density (inverse)
- 30% Waste infrastructure access (dry waste centres within 2km)
- 15% Landfill proximity penalty
- 15% Waste processing capacity

### Builder Reputation (3%)
**Sources:** RERA Karnataka quarterly compliance (Forms 1-3, 70% escrow rule, delivery tracking), BrickFi 2025, MagicBricks/99acres reviews

Area average of active RERA-registered builders. Fallback: citywide top-10 builder average when area-specific data is sparse.

### Delivery Coverage (0.5%)
**Sources:** Zepto delivery areas (Mar 2026), Blinkit dark store expansion (Aug 2025), Swiggy Instamart 10-min coverage, BigBasket (widest coverage since 2011)

**Formula:** `(services_available / 4) * 80 + delivery_time_bonus`

### Business Opportunity (0.5%)
**Sources:** Karnataka Startup Cell, BBMP Trade License 2024-25, NASSCOM Startup Report 2025, RBI/CIBIL MSME data, commercial listings (JustDial, Google Maps), coworking spaces (WeWork, 91springboard, Awfis)

## Composite Score Calculation

```
composite = sum(dimension_score * weight for each dimension)
```

All dimension scores are 0-100. Weights sum to 1.0. The composite is a weighted average on the same 0-100 scale.

**Score Bands:**
- 80-100: Excellent
- 70-79: Very Good
- 60-69: Good
- 50-59: Average
- 40-49: Below Average
- <40: Poor

## Data Pipeline

1. **Seeding**: Pipeline scripts (`backend/app/pipelines/`) fetch data from government APIs, open data portals, and Google Maps. Pre-compute zone scores and store in PostGIS-indexed tables.
2. **Scoring**: At request time, scorers read pre-computed zones — no expensive computation on the hot path.
3. **Verification**: Nightly Claude AI pipeline generates neighborhood narratives, cross-referencing scores against local knowledge. Stored in `neighborhood_verification` with confidence scores (70-95%).
4. **Freshness tracking**: `data_freshness` table records when each data source was last updated.

## Missing Data

When a dimension has no data for a neighborhood, the scorer returns a conservative default score (40-70) with `data_confidence: "low"`. No interpolation is performed — see [ADR-004](docs/decisions/004-missing-data-handling.md) for the rationale.
