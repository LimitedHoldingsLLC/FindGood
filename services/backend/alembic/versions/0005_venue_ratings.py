"""Composite FindGood.Food ratings from official provider scores.

Revision ID: 0005_venue_ratings
Revises: 0004_discovery_filters
Create Date: 2026-08-17

Additive only. Provider star values stay on venue_provider_links. The venue
row stores the Bayesian composite used for consumer filters — not a Google or
Yelp clone.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_venue_ratings"
down_revision: str | None = "0004_discovery_filters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("venues", sa.Column("rating", sa.Numeric(3, 2), nullable=True))
    op.add_column(
        "venues",
        sa.Column("rating_review_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "venues",
        sa.Column("rating_source_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "venues",
        sa.Column("rating_providers", postgresql.ARRAY(sa.String(40)), nullable=False, server_default="{}"),
    )
    op.create_index("ix_venues_rating", "venues", ["rating"])
    op.add_column("venue_provider_links", sa.Column("rating", sa.Numeric(3, 2), nullable=True))
    op.add_column("venue_provider_links", sa.Column("review_count", sa.Integer(), nullable=True))
    op.add_column(
        "venue_provider_links",
        sa.Column("rating_scale", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("venue_provider_links", "rating_scale")
    op.drop_column("venue_provider_links", "review_count")
    op.drop_column("venue_provider_links", "rating")
    op.drop_index("ix_venues_rating", table_name="venues")
    op.drop_column("venues", "rating_providers")
    op.drop_column("venues", "rating_source_count")
    op.drop_column("venues", "rating_review_count")
    op.drop_column("venues", "rating")
