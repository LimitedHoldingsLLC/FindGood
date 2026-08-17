"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, freshnessTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminDeal } from "@/lib/api/types";

export default function AdminDealsPage() {
  const client = useAdminClient();
  const [items, setItems] = useState<AdminDeal[]>([]);
  const [freshness, setFreshness] = useState("");
  const [total, setTotal] = useState(0);

  async function load() {
    if (!client) return;
    const page = await client.opsDeals({ freshness: freshness || undefined, page: 1, page_size: 30 });
    setItems(page.items);
    setTotal(page.total);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, freshness]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Offers</h1>
      <select className="rounded-lg border border-ink/15 px-3 py-2" value={freshness} onChange={(e) => setFreshness(e.target.value)}>
        <option value="">All freshness</option>
        {["fresh", "aging", "stale", "expired", "unverified", "verification_failed"].map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>
      <p className="text-sm text-muted">{total} offers</p>
      <ul className="space-y-2">
        {items.map((deal) => (
          <li key={deal.id} className="rounded-2xl border border-ink/10 bg-card p-4">
            <Link className="font-medium underline" href={`/admin/deals/${deal.id}`}>
              {deal.title}
            </Link>
            <p className="text-sm text-muted">{deal.venue_name}</p>
            <div className="mt-2 flex gap-2">
              <Pill label={deal.freshness_status} tone={freshnessTone(deal.freshness_status)} />
              <Pill label={deal.sighting_state} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
