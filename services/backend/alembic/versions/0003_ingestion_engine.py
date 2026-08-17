"""Ingestion engine: provider links, runs, freshness, review, crawl health.

Revision ID: 0003_ingestion_engine
Revises: 0002_vertical
Create Date: 2026-08-16

Additive only. Existing venue/deal/source rows keep working. New columns have
defaults so a restaurant that was already in the catalog is treated as
unverified until a refresh actually checks it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_ingestion_engine"
down_revision: str | None = "0002_vertical"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("job_type", sa.String(40), nullable=False, server_default="website_crawl"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("requested_by", sa.String(120), nullable=False, server_default="system"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("target_url", sa.String(1000)),
        sa.Column("venue_id", sa.Uuid(), sa.ForeignKey("venues.id")),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id")),
        sa.Column("records_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("robots_blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offers_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offers_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offers_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_category", sa.String(80)),
        sa.Column("error_details", sa.Text()),
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_ingestion_runs_provider", "ingestion_runs", ["provider"])
    op.create_index("ix_ingestion_runs_job_type", "ingestion_runs", ["job_type"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_venue_id", "ingestion_runs", ["venue_id"])
    op.create_index("ix_ingestion_runs_source_id", "ingestion_runs", ["source_id"])
    op.create_index("ix_ingestion_runs_created_at", "ingestion_runs", ["created_at"])

    op.create_table(
        "venue_provider_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("venue_id", sa.Uuid(), sa.ForeignKey("venues.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_business_id", sa.String(200), nullable=False),
        sa.Column("provider_url", sa.String(1000)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_business_id", name="uq_venue_provider_links_provider_id"),
    )
    op.create_index("ix_venue_provider_links_venue_id", "venue_provider_links", ["venue_id"])
    op.create_index("ix_venue_provider_links_provider", "venue_provider_links", ["provider"])

    op.create_table(
        "review_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_type", sa.String(40), nullable=False),
        sa.Column("subject_id", sa.Uuid()),
        sa.Column("reason", sa.String(60), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", sa.String(120)),
    )
    op.create_index("ix_review_items_subject_type", "review_items", ["subject_type"])
    op.create_index("ix_review_items_subject_id", "review_items", ["subject_id"])
    op.create_index("ix_review_items_reason", "review_items", ["reason"])
    op.create_index("ix_review_items_status", "review_items", ["status"])
    op.create_index("ix_review_items_created_at", "review_items", ["created_at"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.Uuid()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_admin_audit_logs_actor", "admin_audit_logs", ["actor"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_logs_target_type", "admin_audit_logs", ["target_type"])
    op.create_index("ix_admin_audit_logs_target_id", "admin_audit_logs", ["target_id"])
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])

    op.create_table(
        "crawl_domains",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("last_http_status", sa.Integer()),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("robots_status", sa.String(40)),
        sa.Column("avg_response_ms", sa.Numeric(10, 2)),
        sa.Column("next_permitted_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("host", name="uq_crawl_domains_host"),
    )
    op.create_index("ix_crawl_domains_host", "crawl_domains", ["host"])
    op.create_index("ix_crawl_domains_next_permitted_at", "crawl_domains", ["next_permitted_at"])

    op.create_table(
        "provider_usage_daily",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rate_limit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("provider", "day", name="uq_provider_usage_daily_provider_day"),
    )
    op.create_index("ix_provider_usage_daily_provider", "provider_usage_daily", ["provider"])
    op.create_index("ix_provider_usage_daily_day", "provider_usage_daily", ["day"])

    op.create_table(
        "error_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(40)),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("url", sa.String(1000)),
        sa.Column("venue_id", sa.Uuid(), sa.ForeignKey("venues.id")),
        sa.Column("ingestion_run_id", sa.Uuid(), sa.ForeignKey("ingestion_runs.id")),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_error_events_provider", "error_events", ["provider"])
    op.create_index("ix_error_events_category", "error_events", ["category"])
    op.create_index("ix_error_events_venue_id", "error_events", ["venue_id"])
    op.create_index("ix_error_events_ingestion_run_id", "error_events", ["ingestion_run_id"])
    op.create_index("ix_error_events_created_at", "error_events", ["created_at"])

    op.add_column("venues", sa.Column("first_seen_at", sa.DateTime(timezone=True)))
    op.add_column("venues", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.add_column("venues", sa.Column("last_verified_at", sa.DateTime(timezone=True)))
    op.add_column("venues", sa.Column("next_refresh_at", sa.DateTime(timezone=True)))
    op.add_column(
        "venues",
        sa.Column("freshness_status", sa.String(32), nullable=False, server_default="unverified"),
    )
    op.add_column("venues", sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_venues_next_refresh_at", "venues", ["next_refresh_at"])
    op.create_index("ix_venues_freshness_status", "venues", ["freshness_status"])

    op.add_column("deals", sa.Column("first_seen_at", sa.DateTime(timezone=True)))
    op.add_column("deals", sa.Column("last_seen_at", sa.DateTime(timezone=True)))
    op.add_column("deals", sa.Column("last_verified_at", sa.DateTime(timezone=True)))
    op.add_column("deals", sa.Column("next_refresh_at", sa.DateTime(timezone=True)))
    op.add_column(
        "deals",
        sa.Column("freshness_status", sa.String(32), nullable=False, server_default="unverified"),
    )
    op.add_column(
        "deals",
        sa.Column("sighting_state", sa.String(32), nullable=False, server_default="active"),
    )
    op.add_column("deals", sa.Column("extraction_method", sa.String(40)))
    op.add_column("deals", sa.Column("consecutive_misses", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("deals", sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("deals", sa.Column("raw_source_text", sa.Text()))
    op.create_index("ix_deals_next_refresh_at", "deals", ["next_refresh_at"])
    op.create_index("ix_deals_freshness_status", "deals", ["freshness_status"])
    op.create_index("ix_deals_sighting_state", "deals", ["sighting_state"])

    op.add_column("sources", sa.Column("next_refresh_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_content_hash", sa.String(64)))
    op.add_column(
        "sources",
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sources_next_refresh_at", "sources", ["next_refresh_at"])

    op.add_column("crawl_runs", sa.Column("ingestion_run_id", sa.Uuid(), sa.ForeignKey("ingestion_runs.id")))
    op.add_column("crawl_runs", sa.Column("pages_discovered", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_runs", sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_runs", sa.Column("pages_skipped", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_runs", sa.Column("robots_blocked", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_runs", sa.Column("requested_by", sa.String(120)))
    op.create_index("ix_crawl_runs_ingestion_run_id", "crawl_runs", ["ingestion_run_id"])


def downgrade() -> None:
    op.drop_index("ix_crawl_runs_ingestion_run_id", table_name="crawl_runs")
    op.drop_column("crawl_runs", "requested_by")
    op.drop_column("crawl_runs", "robots_blocked")
    op.drop_column("crawl_runs", "pages_skipped")
    op.drop_column("crawl_runs", "pages_fetched")
    op.drop_column("crawl_runs", "pages_discovered")
    op.drop_column("crawl_runs", "ingestion_run_id")

    op.drop_index("ix_sources_next_refresh_at", table_name="sources")
    op.drop_column("sources", "consecutive_failures")
    op.drop_column("sources", "last_content_hash")
    op.drop_column("sources", "next_refresh_at")

    op.drop_index("ix_deals_sighting_state", table_name="deals")
    op.drop_index("ix_deals_freshness_status", table_name="deals")
    op.drop_index("ix_deals_next_refresh_at", table_name="deals")
    op.drop_column("deals", "raw_source_text")
    op.drop_column("deals", "failure_count")
    op.drop_column("deals", "consecutive_misses")
    op.drop_column("deals", "extraction_method")
    op.drop_column("deals", "sighting_state")
    op.drop_column("deals", "freshness_status")
    op.drop_column("deals", "next_refresh_at")
    op.drop_column("deals", "last_verified_at")
    op.drop_column("deals", "last_seen_at")
    op.drop_column("deals", "first_seen_at")

    op.drop_index("ix_venues_freshness_status", table_name="venues")
    op.drop_index("ix_venues_next_refresh_at", table_name="venues")
    op.drop_column("venues", "failure_count")
    op.drop_column("venues", "freshness_status")
    op.drop_column("venues", "next_refresh_at")
    op.drop_column("venues", "last_verified_at")
    op.drop_column("venues", "last_seen_at")
    op.drop_column("venues", "first_seen_at")

    op.drop_table("error_events")
    op.drop_table("provider_usage_daily")
    op.drop_table("crawl_domains")
    op.drop_table("admin_audit_logs")
    op.drop_table("review_items")
    op.drop_table("venue_provider_links")
    op.drop_table("ingestion_runs")
