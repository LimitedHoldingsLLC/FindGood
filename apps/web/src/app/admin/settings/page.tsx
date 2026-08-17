"use client";

import { useEffect, useState } from "react";

import { useAdminClient } from "@/features/admin/AdminShell";
import type { AdminAudit } from "@/lib/api/types";

export default function SettingsPage() {
  const client = useAdminClient();
  const [audit, setAudit] = useState<AdminAudit[]>([]);

  useEffect(() => {
    if (!client) return;
    void client.audit().then(setAudit);
  }, [client]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Settings</h1>
      <section className="rounded-2xl border border-ink/10 bg-card p-5 text-sm">
        <h2 className="font-medium">How freshness windows work</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
          <li>Business identity: 30 days</li>
          <li>Phone / website: 21 days</li>
          <li>Hours: 14 days</li>
          <li>Happy hour: 7 days</li>
          <li>Daily specials / limited-time: 3 days</li>
        </ul>
        <p className="mt-3 text-muted">
          Override with BUSINESS_STALE_AFTER_DAYS, HAPPY_HOUR_STALE_AFTER_DAYS, and related env vars. Never paste API
          keys into this UI.
        </p>
      </section>
      <section>
        <h2 className="font-medium">Recent admin actions</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {audit.map((row) => (
            <li key={row.id} className="rounded-xl bg-card p-3">
              {row.actor} · {row.action} · {row.target_type} · {row.created_at}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
