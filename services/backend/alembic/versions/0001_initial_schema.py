"""Initial FindGood schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "venues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("website_url", sa.String(500)),
        sa.Column("phone", sa.String(40)),
        sa.Column("primary_category", sa.String(80), nullable=False, server_default="restaurant"),
        sa.Column("status", sa.String(32), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_venues_slug"),
    )
    op.create_index("ix_venues_slug", "venues", ["slug"])
    op.create_index("ix_venues_status", "venues", ["status"])
    op.create_index("ix_venues_primary_category", "venues", ["primary_category"])

    op.create_table(
        "venue_locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("venue_id", sa.Uuid(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("label", sa.String(120), nullable=False, server_default="Main"),
        sa.Column("address_line1", sa.String(200), nullable=False),
        sa.Column("address_line2", sa.String(200)),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("region", sa.String(80), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column("country", sa.String(2), nullable=False, server_default="US"),
        sa.Column("neighborhood", sa.String(120)),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Los_Angeles"),
        sa.Column("status", sa.String(32), nullable=False, server_default="published"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_venue_locations_venue_id", "venue_locations", ["venue_id"])
    op.create_index("ix_venue_locations_city", "venue_locations", ["city"])
    op.create_index("ix_venue_locations_neighborhood", "venue_locations", ["neighborhood"])
    op.create_index("ix_venue_locations_status", "venue_locations", ["status"])
    op.create_index("ix_venue_locations_geo", "venue_locations", ["latitude", "longitude"])

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("venue_id", sa.Uuid(), sa.ForeignKey("venues.id")),
        sa.Column("source_type", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("canonical_identity", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("crawl_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("crawl_frequency_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("trust_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("respect_robots_txt", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("canonical_identity", name="uq_sources_canonical_identity"),
    )
    op.create_index("ix_sources_venue_id", "sources", ["venue_id"])
    op.create_index("ix_sources_active_crawl", "sources", ["is_active", "crawl_enabled"])

    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="started"),
        sa.Column("fetch_result", sa.String(40)),
        sa.Column("parse_result", sa.String(40)),
        sa.Column("extracted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_category", sa.String(80)),
        sa.Column("error_details", sa.Text()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_crawl_runs_source_id", "crawl_runs", ["source_id"])
    op.create_index("ix_crawl_runs_status", "crawl_runs", ["status"])

    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("crawl_run_id", sa.Uuid(), sa.ForeignKey("crawl_runs.id")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer()),
        sa.Column("content_type", sa.String(200)),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_ref", sa.String(500)),
        sa.Column("raw_content", sa.Text()),
        sa.Column("parser_version", sa.String(40)),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_source_snapshots_source_id", "source_snapshots", ["source_id"])
    op.create_index("ix_source_snapshots_content_hash", "source_snapshots", ["content_hash"])
    op.create_index("ix_source_snapshots_crawl_run_id", "source_snapshots", ["crawl_run_id"])

    op.create_table(
        "deals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("venue_location_id", sa.Uuid(), sa.ForeignKey("venue_locations.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("deal_type", sa.String(40), nullable=False, server_default="other"),
        sa.Column("offering_kind", sa.String(16), nullable=False, server_default="both"),
        sa.Column("status", sa.String(32), nullable=False, server_default="published"),
        sa.Column("publication_state", sa.String(32), nullable=False, server_default="unpublished"),
        sa.Column("source_confidence", sa.Numeric(4, 3), nullable=False, server_default="0.500"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deals_venue_location_id", "deals", ["venue_location_id"])
    op.create_index("ix_deals_status_publication", "deals", ["status", "publication_state"])
    op.create_index("ix_deals_deal_type", "deals", ["deal_type"])
    op.create_index("ix_deals_offering_kind", "deals", ["offering_kind"])

    op.create_table(
        "deal_schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("days_of_week", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("start_time", sa.Time()),
        sa.Column("end_time", sa.Time()),
        sa.Column("ends_at_close", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_until", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_schedules_deal_id", "deal_schedules", ["deal_id"])

    op.create_table(
        "deal_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(80)),
        sa.Column("normal_price", sa.Numeric(10, 2)),
        sa.Column("deal_price", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_items_deal_id", "deal_items", ["deal_id"])

    op.create_table(
        "extraction_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_snapshot_id", sa.Uuid(), sa.ForeignKey("source_snapshots.id"), nullable=False),
        sa.Column("crawl_run_id", sa.Uuid(), sa.ForeignKey("crawl_runs.id")),
        sa.Column("venue_location_id", sa.Uuid(), sa.ForeignKey("venue_locations.id")),
        sa.Column("candidate_type", sa.String(20), nullable=False, server_default="deal"),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("published_deal_id", sa.Uuid(), sa.ForeignKey("deals.id")),
        sa.Column("extractor_version", sa.String(40), nullable=False, server_default="demo-1"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0.500"),
        sa.Column("diagnostic_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_extraction_candidates_snapshot", "extraction_candidates", ["source_snapshot_id"])
    op.create_index("ix_extraction_candidates_review", "extraction_candidates", ["review_status"])
    op.create_index("ix_extraction_candidates_validation", "extraction_candidates", ["validation_status"])

    op.create_table(
        "deal_publications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("extraction_candidates.id")),
        sa.Column("source_snapshot_id", sa.Uuid(), sa.ForeignKey("source_snapshots.id")),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id")),
        sa.Column("published_by", sa.String(80), nullable=False, server_default="system"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("candidate_id", name="uq_deal_publications_candidate_id"),
    )
    op.create_index("ix_deal_publications_deal_id", "deal_publications", ["deal_id"])

    op.create_table(
        "verifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_type", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("verification_type", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="1.000"),
    )
    op.create_index("ix_verifications_subject", "verifications", ["subject_type", "subject_id"])


def downgrade() -> None:
    op.drop_table("verifications")
    op.drop_table("deal_publications")
    op.drop_table("extraction_candidates")
    op.drop_table("deal_items")
    op.drop_table("deal_schedules")
    op.drop_table("deals")
    op.drop_table("source_snapshots")
    op.drop_table("crawl_runs")
    op.drop_table("sources")
    op.drop_table("venue_locations")
    op.drop_table("venues")
