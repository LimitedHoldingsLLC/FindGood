"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminOverview } from "@/lib/api/types";

export default function AdminOverviewPage() {
  const client = useAdminClient();
  const [data, setData] = useState<AdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    client
      .overview()
      .then(setData)
      .catch(() => setError("Could not load overview. Is the API running?"));
  }, [client]);

  if (!client) return null;
  if (error) return <p className="text-terracotta">{error}</p>;
  if (!data) return <p className="text-sm text-muted">Loading mission control…</p>;

  const cards = [
    ["Businesses", data.total_businesses, `+${data.businesses_added_24h} today`],
    ["Active offers", data.total_active_offers, `+${data.offers_added_24h} today`],
    ["Fresh offers", data.verified_offers, `${data.offers_fresh_percent}% of published`],
    ["Stale offers", data.stale_offers, "Need re-check"],
    ["Expired", data.expired_offers, "Known finished"],
    ["Review queue", data.pending_review_items, "Needs a human"],
    ["Runs failed 24h", data.runs_failed_24h, "Partial + failed"],
    ["Crawl errors 24h", data.crawl_failures_24h, "Fetcher / robots / parse"],
  ] as const;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl">Overview</h1>
          <p className="text-sm text-muted">Is FindGood’s data healthy, fresh, and operable?</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-display">{data.freshness_health_percent}%</p>
          <p className="text-xs text-muted">Freshness health</p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Pill label={data.system_working ? "System responding" : "System issue"} tone={data.system_working ? "good" : "bad"} />
        <Pill label={`Businesses fresh ${data.businesses_fresh_percent}%`} tone="neutral" />
        <Pill label={`Offers fresh ${data.offers_fresh_percent}%`} tone={data.offers_fresh_percent >= 80 ? "good" : "warn"} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(([label, value, hint]) => (
          <div key={label} className="rounded-2xl border border-ink/10 bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
            <p className="mt-1 font-display text-3xl">{value}</p>
            <p className="text-xs text-muted">{hint}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted">{data.freshness_note}</p>
      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="rounded-full bg-ink px-4 py-2 text-paper" href="/admin/crawler">
          Crawl a site
        </Link>
        <Link className="rounded-full border border-ink/15 px-4 py-2" href="/admin/freshness">
          Stale offers
        </Link>
        <Link className="rounded-full border border-ink/15 px-4 py-2" href="/admin/review">
          Review queue
        </Link>
      </div>
    </div>
  );
}
