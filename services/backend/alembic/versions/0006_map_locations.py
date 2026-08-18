"""Map eligibility and coordinate provenance on venue_locations.

Revision ID: 0006_map_locations
Revises: 0005_venue_ratings
Create Date: 2026-08-17

Additive only. Existing lat/lng stay required. These columns record how
trustworthy a point is so the consumer map can hide bad pins without
requiring a Google Place ID.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_map_locations"
down_revision: str | None = "0005_venue_ratings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "venue_locations",
        sa.Column("location_confidence", sa.String(32), nullable=False, server_default="high_confidence"),
    )
    op.add_column("venue_locations", sa.Column("geocode_source", sa.String(40), nullable=True))
    op.add_column("venue_locations", sa.Column("geocode_accuracy", sa.String(40), nullable=True))
    op.add_column("venue_locations", sa.Column("coordinates_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("venue_locations", sa.Column("geocoded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("venue_locations", sa.Column("address_hash", sa.String(64), nullable=True))
    op.add_column(
        "venue_locations",
        sa.Column("map_demand_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_venue_locations_confidence", "venue_locations", ["location_confidence"])


def downgrade() -> None:
    op.drop_index("ix_venue_locations_confidence", table_name="venue_locations")
    op.drop_column("venue_locations", "map_demand_count")
    op.drop_column("venue_locations", "address_hash")
    op.drop_column("venue_locations", "geocoded_at")
    op.drop_column("venue_locations", "coordinates_verified_at")
    op.drop_column("venue_locations", "geocode_accuracy")
    op.drop_column("venue_locations", "geocode_source")
    op.drop_column("venue_locations", "location_confidence")
