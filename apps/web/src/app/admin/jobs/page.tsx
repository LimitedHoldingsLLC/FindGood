"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, runTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminRun } from "@/lib/api/types";

export default function JobsPage() {
  const client = useAdminClient();
  const [items, setItems] = useState<AdminRun[]>([]);

  useEffect(() => {
    if (!client) return;
    void client.runs({ page_size: 30 }).then((page) => setItems(page.items));
  }, [client]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Jobs / queue</h1>
      <p className="text-sm text-muted">
        Long work is enqueued to Redis and run by `python -m app.workers.runner`. If the worker is not running, use
        sync crawl only for local demos.
      </p>
      <ul className="space-y-2 text-sm">
        {items.map((run) => (
          <li key={run.id} className="flex justify-between gap-2 rounded-2xl border border-ink/10 bg-card p-4">
            <Link className="underline" href={`/admin/runs/${run.id}`}>
              {run.job_type} · {run.provider}
            </Link>
            <Pill label={run.status} tone={runTone(run.status)} />
          </li>
        ))}
      </ul>
    </div>
  );
}
