"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, freshnessTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminFreshness } from "@/lib/api/types";

export default function FreshnessPage() {
  const client = useAdminClient();
  const [data, setData] = useState<AdminFreshness | null>(null);
  const [bucket, setBucket] = useState("stale");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    void client.freshness({ freshness: bucket, page_size: 20 }).then(setData);
  }, [client, bucket]);

  if (!client || !data) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Data freshness</h1>
      <p className="text-sm text-muted">
        Fresh means recently verified. Stale means we have not re-checked in time. Expired means the promotion’s end
        date has passed.
      </p>
      <div className="flex flex-wrap gap-2">
        {Object.entries(data.buckets).map(([name, count]) => (
          <button
            key={name}
            className={`rounded-full px-3 py-1 text-sm ${bucket === name ? "bg-ink text-paper" : "border border-ink/15"}`}
            onClick={() => setBucket(name)}
          >
            {name} ({count})
          </button>
        ))}
      </div>
      <button
        className="rounded-full bg-ink px-4 py-2 text-sm text-paper"
        onClick={async () => {
          const result = await client.queueStale();
          setMessage(`Queued ${result.queued} refreshes`);
        }}
      >
        Queue stale refreshes
      </button>
      {message ? <p className="text-sm text-forest">{message}</p> : null}
      <ul className="space-y-2">
        {data.items.map((deal) => (
          <li key={deal.id} className="rounded-2xl border border-ink/10 bg-card p-4">
            <Link className="underline" href={`/admin/deals/${deal.id}`}>
              {deal.title}
            </Link>
            <div className="mt-1">
              <Pill label={deal.freshness_status} tone={freshnessTone(deal.freshness_status)} />
            </div>
            <p className="text-xs text-muted">Last verified {deal.last_verified_at ?? "never"}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
