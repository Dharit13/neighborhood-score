import os
import asyncpg
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Parse connection params for keyword-based connections (avoids URL encoding issues)
DB_HOST = os.getenv("DB_HOST", "aws-0-ap-south-1.pooler.supabase.com")
DB_PORT = int(os.getenv("DB_PORT", "6543"))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres.usizbvzwcftfqpovtsxf")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Jskjhj!41516")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            min_size=2,
            max_size=10,
            command_timeout=30,
            statement_cache_size=0,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_sync_conn():
    """Synchronous connection for seed/pipeline scripts."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def seed_execute(sql: str, params: tuple | list | None = None):
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def seed_executemany(sql: str, params_list: list[tuple]):
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, params_list)
        conn.commit()
    finally:
        conn.close()


def run_sql_file(filepath: str):
    with open(filepath) as f:
        sql = f.read()
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"  OK: {filepath}")
    finally:
        conn.close()
