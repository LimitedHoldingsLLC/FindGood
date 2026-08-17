"""Add vertical taxonomy columns. Existing rows become food.

Revision ID: 0002_vertical
Revises: 0001_initial
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_vertical"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "venues",
        sa.Column("vertical", sa.String(32), nullable=False, server_default="food"),
    )
    op.add_column(
        "deals",
        sa.Column("vertical", sa.String(32), nullable=False, server_default="food"),
    )
    op.create_index("ix_venues_vertical", "venues", ["vertical"])
    op.create_index("ix_deals_vertical", "deals", ["vertical"])
    op.create_index("ix_deals_vertical_publication", "deals", ["vertical", "status", "publication_state"])


def downgrade() -> None:
    op.drop_index("ix_deals_vertical_publication", table_name="deals")
    op.drop_index("ix_deals_vertical", table_name="deals")
    op.drop_index("ix_venues_vertical", table_name="venues")
    op.drop_column("deals", "vertical")
    op.drop_column("venues", "vertical")
