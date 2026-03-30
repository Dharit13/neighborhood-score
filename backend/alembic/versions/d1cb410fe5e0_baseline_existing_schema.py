"""baseline: existing schema

Marks the existing database schema (001_create_tables.sql + subsequent migrations)
as the Alembic baseline. No DDL is executed — the tables already exist in Supabase.

Run `alembic stamp head` on an existing database to mark it as up-to-date.

Revision ID: d1cb410fe5e0
Revises:
Create Date: 2026-03-28 13:47:23.140623

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'd1cb410fe5e0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline — existing schema already applied via supabase/migrations/."""
    pass


def downgrade() -> None:
    """Cannot downgrade past baseline."""
    pass
