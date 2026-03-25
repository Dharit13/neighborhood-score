"""
CLI runner for pipeline operations.
Usage:
    python -m app.pipelines.runner migrate
    python -m app.pipelines.runner seed --all
    python -m app.pipelines.runner seed --neighborhoods
    python -m app.pipelines.runner seed --transit
    python -m app.pipelines.runner seed --points
    python -m app.pipelines.runner seed --zones
    python -m app.pipelines.runner seed --prices
    python -m app.pipelines.runner seed --infra
    python -m app.pipelines.runner verify [--all | NEIGHBORHOOD_NAME]
    python -m app.pipelines.runner status
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()


def cmd_migrate():
    from app.db import run_sql_file
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")
    print("Running migrations...")
    run_sql_file(os.path.join(migrations_dir, "001_create_tables.sql"))
    run_sql_file(os.path.join(migrations_dir, "002_create_indexes.sql"))
    run_sql_file(os.path.join(migrations_dir, "003_add_cleanliness.sql"))
    run_sql_file(os.path.join(migrations_dir, "004_add_ward_mapping.sql"))
    print("Migrations complete.")


def cmd_seed(args):
    if args.all:
        from app.pipelines.seed_all import run
        run()
        return

    if args.neighborhoods:
        from app.pipelines.seed_neighborhoods import seed
        seed()
    if args.transit:
        from app.pipelines.seed_transit import seed
        seed()
    if args.points:
        from app.pipelines.seed_points import seed
        seed()
    if args.zones:
        from app.pipelines.seed_zones import seed
        seed()
    if args.prices:
        from app.pipelines.seed_prices import seed
        seed()
    if args.infra:
        from app.pipelines.seed_infra import seed
        seed()


def cmd_fetch(args):
    """Fetch live data from APIs and open data sources."""
    if args.bus_stops:
        from app.pipelines.fetch_bus_stops import fetch
        fetch()
    if args.flood:
        from app.pipelines.fetch_flood_risk import fetch
        fetch()
    if args.commute:
        from app.pipelines.fetch_commute_times import fetch
        fetch()
    if args.delivery:
        from app.pipelines.fetch_delivery_coverage import fetch
        fetch()
    if args.noise:
        from app.pipelines.fetch_noise_zones import fetch
        fetch()
    if args.builders:
        from app.pipelines.fetch_rera_builders import fetch
        fetch()
    if args.police:
        from app.pipelines.fetch_police_stations import fetch
        fetch()
    if args.slums:
        from app.pipelines.fetch_slum_data import fetch
        fetch()
    if args.waste:
        from app.pipelines.fetch_waste_infra import fetch
        fetch()
    if args.wards:
        from app.pipelines.fetch_ward_mapping import fetch
        fetch()
    if args.all:
        print("Fetching all live data sources...")
        from app.pipelines.fetch_bus_stops import fetch as fb
        fb()
        from app.pipelines.fetch_flood_risk import fetch as ff
        ff()
        from app.pipelines.fetch_delivery_coverage import fetch as fd
        fd()
        from app.pipelines.fetch_noise_zones import fetch as fn
        fn()
        from app.pipelines.fetch_rera_builders import fetch as fr
        fr()
        from app.pipelines.fetch_police_stations import fetch as fp
        fp()
        from app.pipelines.fetch_slum_data import fetch as fsl
        fsl()
        from app.pipelines.fetch_waste_infra import fetch as fwi
        fwi()
        from app.pipelines.fetch_ward_mapping import fetch as fwm
        fwm()
        print("\nNote: Commute times require Google Maps API credits.")
        print("Run separately: python -m app.pipelines.runner fetch --commute")


def cmd_verify(args):
    from app.pipelines.verify_ai import verify
    if args.all:
        verify(neighborhood_name=None)
    elif args.name:
        verify(neighborhood_name=args.name)
    else:
        verify(neighborhood_name=None)


def cmd_refresh(args):
    if args.walkability:
        from app.pipelines.pipeline_walkability import run
        run(neighborhood_name=args.name)
    else:
        print("Specify what to refresh: --walkability")


def cmd_status():
    from app.db import get_sync_conn
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, record_count, status, last_seeded_at "
                "FROM data_freshness ORDER BY table_name"
            )
            rows = cur.fetchall()
            if not rows:
                print("No data freshness records. Run 'seed --all' first.")
                return
            print(f"{'Table':<30} {'Rows':>8} {'Status':<8} {'Last Seeded'}")
            print("-" * 75)
            for table, count, status, seeded in rows:
                seeded_str = seeded.strftime("%Y-%m-%d %H:%M") if seeded else "never"
                print(f"{table:<30} {count:>8} {status:<8} {seeded_str}")

            # Buyer perspective tables
            buyer_tables = ["flood_risk", "commute_times", "delivery_coverage", "noise_zones"]
            for t in buyer_tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    c = cur.fetchone()[0]
                    if c > 0:
                        print(f"{t:<30} {c:>8} {'live':<8} (fetched from API)")
                except Exception:
                    pass

            # AI verification summary
            cur.execute(
                """SELECT COUNT(*) as total,
                          AVG(confidence) as avg_confidence,
                          COUNT(*) FILTER (WHERE confidence < 70) as low_confidence
                   FROM neighborhood_verification"""
            )
            vrow = cur.fetchone()
            if vrow and vrow[0] > 0:
                print(f"\nAI Verification: {vrow[0]} neighborhoods verified, "
                      f"avg confidence {vrow[1]:.0f}%, "
                      f"{vrow[2]} low-confidence")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Data pipeline runner")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("migrate", help="Run schema migrations")

    sub_seed = subparsers.add_parser("seed", help="Seed data from JSON files")
    sub_seed.add_argument("--all", action="store_true", help="Run all seeds (migrations + data)")
    sub_seed.add_argument("--neighborhoods", action="store_true")
    sub_seed.add_argument("--transit", action="store_true")
    sub_seed.add_argument("--points", action="store_true")
    sub_seed.add_argument("--zones", action="store_true")
    sub_seed.add_argument("--prices", action="store_true")
    sub_seed.add_argument("--infra", action="store_true")

    sub_verify = subparsers.add_parser("verify", help="Run AI verification")
    sub_verify.add_argument("--all", action="store_true", help="Verify all neighborhoods")
    sub_verify.add_argument("--name", type=str, help="Verify specific neighborhood")

    sub_refresh = subparsers.add_parser("refresh", help="Refresh live data from APIs")
    sub_refresh.add_argument("--walkability", action="store_true", help="Refresh walkability via Overpass")
    sub_refresh.add_argument("--name", type=str, help="Refresh specific neighborhood only")

    sub_fetch = subparsers.add_parser("fetch", help="Fetch live data from APIs and open data sources")
    sub_fetch.add_argument("--all", action="store_true", help="Fetch all live data (except commute)")
    sub_fetch.add_argument("--bus-stops", action="store_true", help="Download 9K BMTC bus stops from GitHub")
    sub_fetch.add_argument("--flood", action="store_true", help="Download BBMP flood risk data")
    sub_fetch.add_argument("--commute", action="store_true", help="Fetch commute times via Google Maps API (~$10)")
    sub_fetch.add_argument("--delivery", action="store_true", help="Check delivery coverage per neighborhood")
    sub_fetch.add_argument("--noise", action="store_true", help="Compute noise zones from CPCB + flight paths")
    sub_fetch.add_argument("--builders", action="store_true", help="Verify builder data against RERA portal")
    sub_fetch.add_argument("--police", action="store_true", help="Download police station locations from KSRSAC")
    sub_fetch.add_argument("--slums", action="store_true", help="Download Bengaluru slum locations from data.opencity.in")
    sub_fetch.add_argument("--waste", action="store_true", help="Download BBMP waste infrastructure from data.opencity.in")
    sub_fetch.add_argument("--wards", action="store_true", help="Download GBA 369 ward boundaries and map to neighborhoods")

    subparsers.add_parser("status", help="Show data freshness + verification status")

    args = parser.parse_args()

    if args.command == "migrate":
        cmd_migrate()
    elif args.command == "seed":
        cmd_seed(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "refresh":
        cmd_refresh(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
