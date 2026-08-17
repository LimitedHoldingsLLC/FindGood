"""Venue discovery attributes for consumer filters.

Revision ID: 0004_discovery_filters
Revises: 0003_ingestion_engine
Create Date: 2026-08-17

Additive only. Existing venues get empty cuisine/drink/feature arrays and
no price level until an operator or ingest fill them in.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_discovery_filters"
down_revision: str | None = "0003_ingestion_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "venues",
        sa.Column("cuisines", postgresql.ARRAY(sa.String(40)), nullable=False, server_default="{}"),
    )
    op.add_column("venues", sa.Column("price_level", sa.Integer(), nullable=True))
    op.add_column(
        "venues",
        sa.Column("drink_kinds", postgresql.ARRAY(sa.String(40)), nullable=False, server_default="{}"),
    )
    op.add_column(
        "venues",
        sa.Column("accepts_reservations", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "venues",
        sa.Column("features", postgresql.ARRAY(sa.String(40)), nullable=False, server_default="{}"),
    )
    op.create_index("ix_venues_price_level", "venues", ["price_level"])
    op.create_index("ix_venues_accepts_reservations", "venues", ["accepts_reservations"])


def downgrade() -> None:
    op.drop_index("ix_venues_accepts_reservations", table_name="venues")
    op.drop_index("ix_venues_price_level", table_name="venues")
    op.drop_column("venues", "features")
    op.drop_column("venues", "accepts_reservations")
    op.drop_column("venues", "drink_kinds")
    op.drop_column("venues", "price_level")
    op.drop_column("venues", "cuisines")
