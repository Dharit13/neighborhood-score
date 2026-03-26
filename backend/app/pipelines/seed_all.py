"""
Orchestrator: run all seed scripts in dependency order, update data_freshness.
Usage: python -m app.pipelines.seed_all
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import run_sql_file, get_sync_conn


def _update_freshness(cur, source: str, table: str, count: int):
    cur.execute(
        """INSERT INTO data_freshness (source_name, table_name, last_seeded_at, record_count, status)
           VALUES (%s, %s, now(), %s, 'fresh')
           ON CONFLICT (source_name, table_name) DO UPDATE SET
             last_seeded_at = now(), record_count = %s, status = 'fresh'""",
        (source, table, count, count),
    )


def run():
    start = time.time()
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")

    print("=== Phase 1: Schema migrations ===")
    run_sql_file(os.path.join(migrations_dir, "001_create_tables.sql"))
    run_sql_file(os.path.join(migrations_dir, "002_create_indexes.sql"))
    run_sql_file(os.path.join(migrations_dir, "003_add_cleanliness.sql"))
    run_sql_file(os.path.join(migrations_dir, "004_add_ward_mapping.sql"))
    run_sql_file(os.path.join(migrations_dir, "006_property_intelligence.sql"))

    print("\n=== Phase 2: Seed data (curated JSON) ===")

    print("\n[1/8] Neighborhoods...")
    from app.pipelines.seed_neighborhoods import seed as seed_neighborhoods
    seed_neighborhoods()

    print("\n[2/8] Transit (metro, bus, train, tech parks)...")
    from app.pipelines.seed_transit import seed as seed_transit
    seed_transit()

    print("\n[3/8] Points (hospitals, schools, police, AQI)...")
    from app.pipelines.seed_points import seed as seed_points
    seed_points()

    print("\n[4/8] Zones (safety, water, power, walkability)...")
    from app.pipelines.seed_zones import seed as seed_zones
    seed_zones()

    print("\n[5/8] Prices, builders, business opportunity...")
    from app.pipelines.seed_prices import seed as seed_prices
    seed_prices()

    print("\n[6/8] Future infrastructure...")
    from app.pipelines.seed_infra import seed as seed_infra
    seed_infra()

    print("\n=== Phase 3: Fetch live data (APIs + open data) ===")

    print("\n[7/9] Bus stops (data.opencity.in / BMTC GTFS)...")
    from app.pipelines.fetch_bus_stops import fetch as fetch_bus_stops
    fetch_bus_stops()

    print("\n[8/9] Police stations (KSRSAC KML)...")
    from app.pipelines.fetch_police_stations import fetch as fetch_police
    fetch_police()

    print("\n[9/9] Buyer perspective (flood, delivery, noise)...")
    from app.pipelines.fetch_flood_risk import fetch as fetch_flood
    fetch_flood()
    from app.pipelines.fetch_delivery_coverage import fetch as fetch_delivery
    fetch_delivery()
    from app.pipelines.fetch_noise_zones import fetch as fetch_noise
    fetch_noise()

    print("\n[10/11] Slum zones (data.opencity.in KML)...")
    from app.pipelines.fetch_slum_data import fetch as fetch_slums
    fetch_slums()

    print("\n[11/12] Waste infrastructure (BBMP KMLs)...")
    from app.pipelines.fetch_waste_infra import fetch as fetch_waste
    fetch_waste()

    print("\n[12/12] Ward mapping (GBA 369 wards)...")
    from app.pipelines.fetch_ward_mapping import fetch as fetch_wards
    fetch_wards()

    print("\n=== Phase 4: RERA builder verification ===")
    from app.pipelines.fetch_rera_builders import fetch as fetch_rera
    fetch_rera()

    print("\n=== Phase 5: Property Intelligence ===")

    print("\n[1/4] K-RERA scraper (discovery + enrichment + builder projects)...")
    from app.pipelines.scrape_krera import scrape_all_builders
    scrape_all_builders()

    print("\n[2/4] Landmarks registry...")
    from app.pipelines.seed_landmarks import seed as seed_landmarks
    seed_landmarks()

    print("\n[3/4] Infrastructure projects (enhanced with realistic ETAs)...")
    from app.pipelines.seed_infrastructure import seed as seed_infrastructure
    seed_infrastructure()

    print("\n[4/4] Areas (126 Bangalore localities)...")
    from app.pipelines.seed_areas import seed as seed_areas
    seed_areas()

    print("\n=== Updating data_freshness ===")
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            tables = [
                "neighborhoods", "metro_stations", "bus_stops", "train_stations",
                "tech_parks", "hospitals", "schools", "police_stations", "aqi_stations",
                "safety_zones", "water_zones", "power_zones", "walkability_zones",
                "property_prices", "builders", "business_opportunity",
                "future_infra_projects", "future_infra_stations",
                "flood_risk", "delivery_coverage", "noise_zones",
                "slum_zones", "waste_infrastructure", "ward_mapping",
                "landmark_registry", "infrastructure_projects", "areas", "builder_projects",
            ]
            for t in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    count = cur.fetchone()[0]
                    _update_freshness(cur, "seed_all", t, count)
                except Exception:
                    conn.rollback()
        conn.commit()
    finally:
        conn.close()

    elapsed = round(time.time() - start, 1)
    print(f"\n=== Done in {elapsed}s ===")


if __name__ == "__main__":
    run()
