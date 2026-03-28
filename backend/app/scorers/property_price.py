"""
Property Price & Affordability Score (0-100)

METHODOLOGY: RBI Residential Asset Price Monitoring + ANAROCK H1 2025
Source: RBI (rbi.org.in/Scripts/PublicationsView.aspx?id=16223)
        ANAROCK Homebuyer Sentiment Survey H1 2025

EMI-to-Income ratio methodology:
  - EMI per lakh at 8.00%/20yr = Rs 836/month (SBI/HDFC typical for salaried, 2026)
  - Benchmark: 20 LPA CTC tech professional = Rs 1,15,000/month take-home
  - < 30% EMI/Income = Comfortable (80-100)
  - 30-40% = Affordable (60-80)
  - 40-50% = Stretched (40-60)
  - 50-70% = Unaffordable (20-40)
  - > 70% = Severely unaffordable (0-20)

National context: India average P/I ratio = 7.5 (ANAROCK 2024).
Karnataka P/I ratio = 14.0 (IndiaDataMap 2025 State Rankings).
"""

from app.db import get_pool
from app.models import NearbyDetail, ScoreResult

# RBI + bank rate benchmarks (March 2026)
RBI_EMI_PER_LAKH_20YR = 836
BENCHMARK_MONTHLY_INCOME = 115_000  # 20 LPA CTC take-home

# EMI/Income scoring bands (RBI + ANAROCK methodology)
AFFORDABILITY_BANDS = [
    (0, 30, 80, 100, "Comfortable"),
    (30, 40, 60, 80, "Affordable"),
    (40, 50, 40, 60, "Stretched"),
    (50, 70, 20, 40, "Unaffordable"),
    (70, 200, 0, 20, "Severely Unaffordable"),
]

SOURCES = [
    "RBI Residential Asset Price Monitoring (rbi.org.in)",
    "ANAROCK Homebuyer Sentiment Survey H1 2025",
    "EMI at 8.00% p.a. / 20yr tenure (SBI/HDFC typical, Mar 2026)",
    "Benchmark: 20 LPA CTC tech professional, Bangalore",
    "99acres / MagicBricks property rate data (Mar 2026)",
]


def _emi_to_score(emi_pct: float) -> tuple[float, str]:
    """Convert EMI/Income % to affordability score using RBI bands."""
    for lo, hi, score_lo, score_hi, label in AFFORDABILITY_BANDS:
        if lo <= emi_pct < hi:
            # Linear interpolation within the band
            ratio = (emi_pct - lo) / (hi - lo)
            score = score_hi - ratio * (score_hi - score_lo)
            return round(max(0, min(100, score)), 1), label
    return 0.0, "Severely Unaffordable"


async def compute_property_price_info(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        area = await conn.fetchrow(
            """SELECT area, avg_price_sqft, price_range_low, price_range_high,
                      avg_2bhk_lakh, avg_3bhk_lakh, avg_2bhk_rent, avg_3bhk_rent,
                      yoy_growth_pct, rental_yield_pct, emi_to_income_pct,
                      affordability_score as stored_affordability, affordability_label,
                      avg_maintenance_monthly, resale_avg_days_on_market,
                      ST_Y(center_geog::geometry) as latitude,
                      ST_X(center_geog::geometry) as longitude,
                      ST_Distance(center_geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM property_prices
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon,
            lat,
        )

    if not area:
        return ScoreResult(score=50.0, label="No Data", data_confidence="low", sources=["No property price data"])

    # Compute EMI/Income ratio using RBI methodology
    avg_2bhk = area["avg_2bhk_lakh"]
    monthly_emi = avg_2bhk * RBI_EMI_PER_LAKH_20YR
    emi_income_pct = (monthly_emi / BENCHMARK_MONTHLY_INCOME) * 100

    affordability_score, affordability_label = _emi_to_score(emi_income_pct)

    avg = area["avg_price_sqft"]
    details = [
        NearbyDetail(
            name=f"{area['area']}: Avg \u20b9{avg:,}/sqft | 2BHK ~\u20b9{avg_2bhk}L | EMI {emi_income_pct:.0f}% of income",
            distance_km=round(area["distance_km"], 2),
            category="property_price",
            latitude=area["latitude"],
            longitude=area["longitude"],
        )
    ]

    # Rental estimation
    avg_2bhk_rent = area["avg_2bhk_rent"] or 0
    avg_3bhk_rent = area["avg_3bhk_rent"] or 0
    rent_to_income_pct = round((avg_2bhk_rent / BENCHMARK_MONTHLY_INCOME) * 100, 1) if avg_2bhk_rent else None

    # Rent vs Buy recommendation based on EMI-to-rent comparison
    if avg_2bhk_rent and monthly_emi:
        emi_rent_ratio = monthly_emi / avg_2bhk_rent
        if emi_rent_ratio > 2.5:
            rental_recommendation = "Rent"
            rental_reasoning = f"EMI (₹{round(monthly_emi):,}) is {emi_rent_ratio:.1f}x the rent (₹{avg_2bhk_rent:,})"
        elif emi_rent_ratio > 1.5:
            rental_recommendation = "Rent (consider buying if staying 7+ years)"
            rental_reasoning = f"EMI (₹{round(monthly_emi):,}) is {emi_rent_ratio:.1f}x the rent (₹{avg_2bhk_rent:,})"
        elif emi_rent_ratio > 0.8:
            rental_recommendation = "Buy"
            rental_reasoning = f"EMI (₹{round(monthly_emi):,}) is close to rent (₹{avg_2bhk_rent:,}) — equity building"
        else:
            rental_recommendation = "Strong Buy"
            rental_reasoning = f"EMI (₹{round(monthly_emi):,}) is below rent (₹{avg_2bhk_rent:,})"
    else:
        rental_recommendation = None
        rental_reasoning = None

    return ScoreResult(
        score=affordability_score,
        label=f"\u20b9{avg:,}/sqft ({affordability_label})",
        details=details,
        breakdown={
            "methodology": "RBI EMI/Income ratio — 8.00%/20yr, 20 LPA benchmark",
            "area": area["area"],
            "avg_price_per_sqft": avg,
            "avg_2bhk_price_lakh": avg_2bhk,
            "monthly_emi_rs": round(monthly_emi),
            "benchmark_income_rs": BENCHMARK_MONTHLY_INCOME,
            "emi_to_income_pct": round(emi_income_pct, 1),
            "affordability_label": affordability_label,
            "avg_2bhk_rent": avg_2bhk_rent,
            "avg_3bhk_rent": avg_3bhk_rent,
            "rent_to_income_pct": rent_to_income_pct,
            "rental_recommendation": rental_recommendation,
            "rental_reasoning": rental_reasoning,
            "yoy_growth_pct": round(float(area["yoy_growth_pct"] or 0), 1),
            "rental_yield_pct": round(float(area["rental_yield_pct"] or 0), 1),
            "avg_maintenance_monthly": area["avg_maintenance_monthly"],
            "resale_avg_days_on_market": area["resale_avg_days_on_market"],
            "price_range_low": area["price_range_low"],
            "price_range_high": area["price_range_high"],
        },
        sources=SOURCES,
    )
