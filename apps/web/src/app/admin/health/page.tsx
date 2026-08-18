"use client";

import { useEffect, useState } from "react";

import { Pill, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminSystem } from "@/lib/api/types";

export default function HealthPage() {
  const client = useAdminClient();
  const [data, setData] = useState<AdminSystem | null>(null);

  useEffect(() => {
    if (!client) return;
    void client.system().then(setData);
  }, [client]);

  if (!client || !data) return <p className="text-sm text-muted">Loading…</p>;

  const rows = [
    ["API", data.api],
    ["Postgres", data.postgres],
    ["Redis", data.redis],
    ["Worker / queue", data.worker],
    ["Crawler", data.crawler],
    ["Google Places", data.google],
    ["Yelp", data.yelp],
    ["Tripadvisor", data.tripadvisor ?? "not configured"],
    ["OpenTable", data.opentable],
    ["Maps", data.maps ?? "healthy"],
    ["Geocoding", data.geocoding ?? "not configured"],
  ] as const;

  function tone(value: string) {
    if (value === "healthy") return "good" as const;
    if (value === "not configured") return "warn" as const;
    return "bad" as const;
  }

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">System health</h1>
      <div className="grid gap-3 sm:grid-cols-2">
        {rows.map(([name, value]) => (
          <div key={name} className="flex items-center justify-between rounded-2xl border border-ink/10 bg-card p-4">
            <span>{name}</span>
            <Pill label={value} tone={tone(value)} />
          </div>
        ))}
      </div>
    </div>
  );
}
