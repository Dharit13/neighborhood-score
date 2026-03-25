import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CURATED_DIR = DATA_DIR / "curated"
RAW_DIR = DATA_DIR / "raw"

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_USER_AGENT = "bangalore-neighborhood-score/1.0"

BANGALORE_BBOX = {
    "south": 12.7342,
    "west": 77.3791,
    "north": 13.1739,
    "east": 77.8826,
}

BANGALORE_CENTER = (12.9716, 77.5946)

WALKING_SPEED_KMH = 5.0

# Composite score weights — derived from ANAROCK Homebuyer Sentiment Survey H1 2025
# Raw survey (post-COVID): Safety 43%, Price/Affordability 49%, Amenities 38%,
# Commute 14%, School 6%. Mapped to our 17 dimensions and normalized to 1.0.
# Bangalore-specific adjustments: flood risk elevated (BuildWatch 2025 — #1 concern),
# water supply elevated (BWSSB scarcity crisis), commute added (ORR/tech corridor pain).
# Cleanliness added: slum proximity + BBMP waste infrastructure (data.opencity.in).
# Source: ANAROCK H1 2025, BuildWatch Bangalore 2025, Knight Frank India 2025
SCORE_WEIGHTS = {
    "safety":               0.12,
    "affordability":        0.12,
    "transit_access":       0.09,
    "flood_risk":           0.08,
    "commute":              0.08,
    "walkability":          0.07,
    "hospital_access":      0.07,
    "water_supply":         0.07,
    "air_quality":          0.06,
    "school_access":        0.05,
    "noise":                0.04,
    "power_reliability":    0.04,
    "future_infrastructure": 0.04,
    "cleanliness":          0.03,
    "builder_reputation":   0.03,
    "delivery_coverage":    0.005,
    "business_opportunity": 0.005,
}
