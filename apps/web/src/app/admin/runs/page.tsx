"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, runTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminRun } from "@/lib/api/types";

export default function RunsPage() {
  const client = useAdminClient();
  const [items, setItems] = useState<AdminRun[]>([]);
  const [provider, setProvider] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!client) return;
    void client
      .runs({ provider: provider || undefined, status: status || undefined, page_size: 30 })
      .then((page) => setItems(page.items));
  }, [client, provider, status]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Ingestion runs</h1>
      <div className="flex gap-2">
        <input className="rounded-lg border border-ink/15 px-3 py-2" placeholder="provider" value={provider} onChange={(e) => setProvider(e.target.value)} />
        <input className="rounded-lg border border-ink/15 px-3 py-2" placeholder="status" value={status} onChange={(e) => setStatus(e.target.value)} />
      </div>
      <ul className="space-y-2 text-sm">
        {items.map((run) => (
          <li key={run.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-ink/10 bg-card p-4">
            <div>
              <Link className="underline" href={`/admin/runs/${run.id}`}>
                {run.job_type}
              </Link>
              <p className="text-muted">
                {run.provider} · {run.target_url ?? "—"} · created {run.records_created} · offers {run.offers_created}
              </p>
            </div>
            <Pill label={run.status} tone={runTone(run.status)} />
          </li>
        ))}
      </ul>
    </div>
  );
}
