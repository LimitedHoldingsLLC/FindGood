"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Pill, freshnessTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminDeal } from "@/lib/api/types";

export default function AdminDealDetailPage() {
  const params = useParams<{ id: string }>();
  const client = useAdminClient();
  const [deal, setDeal] = useState<AdminDeal | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    void client.opsDeal(params.id).then(setDeal);
  }, [client, params.id]);

  if (!client || !deal) return <p className="text-sm text-muted">Loading…</p>;

  async function act(label: string, fn: () => Promise<AdminDeal>) {
    setDeal(await fn());
    setMessage(label);
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase text-muted">Offer</p>
        <h1 className="font-display text-4xl">{deal.title}</h1>
        <p className="text-sm text-muted">{deal.venue_name}</p>
      </div>
      {message ? <p className="text-sm text-forest">{message}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Pill label={deal.freshness_status} tone={freshnessTone(deal.freshness_status)} />
        <Pill label={deal.sighting_state} />
        <Pill label={deal.extraction_method ?? "unknown"} />
      </div>
      <p className="whitespace-pre-wrap text-sm">{deal.description}</p>
      {deal.raw_source_text ? (
        <section className="rounded-2xl bg-ink/5 p-4 text-xs">
          <p className="font-medium">Source evidence (not overwritten by edits)</p>
          <pre className="mt-2 whitespace-pre-wrap">{deal.raw_source_text}</pre>
        </section>
      ) : null}
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div>First seen: {deal.first_seen_at ?? "—"}</div>
        <div>Last seen: {deal.last_seen_at ?? "—"}</div>
        <div>Last verified: {deal.last_verified_at ?? "—"}</div>
        <div>Next refresh: {deal.next_refresh_at ?? "—"}</div>
        <div>Misses: {deal.consecutive_misses}</div>
        <div>Confidence: {deal.source_confidence}</div>
      </dl>
      <div className="flex flex-wrap gap-2 text-sm">
        <button className="rounded-full bg-ink px-4 py-2 text-paper" onClick={() => act("Verified", () => client.verifyDeal(deal.id, "Verified manually from admin"))}>
          Verify
        </button>
        <button className="rounded-full border border-ink/15 px-4 py-2" onClick={() => act("Expired", () => client.expireDeal(deal.id))}>
          Mark expired
        </button>
        <button className="rounded-full border border-ink/15 px-4 py-2" onClick={() => act("Restored", () => client.restoreDeal(deal.id))}>
          Restore
        </button>
        <button className="rounded-full border border-terracotta/40 px-4 py-2 text-terracotta" onClick={() => act("Rejected", () => client.rejectDeal(deal.id))}>
          Reject
        </button>
        {deal.venue_id ? (
          <Link className="rounded-full border border-ink/15 px-4 py-2" href={`/admin/venues/${deal.venue_id}`}>
            Open business
          </Link>
        ) : null}
      </div>
    </div>
  );
}
