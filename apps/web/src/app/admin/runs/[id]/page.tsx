"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Pill, runTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminRun } from "@/lib/api/types";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const client = useAdminClient();
  const [run, setRun] = useState<AdminRun | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    void client.run(params.id).then(setRun);
  }, [client, params.id]);

  useEffect(() => {
    if (!client || !run || !["queued", "running"].includes(run.status)) return;
    const timer = setInterval(async () => setRun(await client.run(run.id)), 3000);
    return () => clearInterval(timer);
  }, [client, run]);

  if (!client || !run) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Run {run.id.slice(0, 8)}</h1>
      <Pill label={run.status} tone={runTone(run.status)} />
      {message ? <p className="text-sm text-forest">{message}</p> : null}
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div>Provider: {run.provider}</div>
        <div>Job: {run.job_type}</div>
        <div>Requested by: {run.requested_by}</div>
        <div>URL: {run.target_url ?? "—"}</div>
        <div>Pages fetched: {run.pages_fetched}</div>
        <div>Robots blocked: {run.robots_blocked}</div>
        <div>Records created: {run.records_created}</div>
        <div>Records updated: {run.records_updated}</div>
        <div>Offers created: {run.offers_created}</div>
        <div>Retries: {run.retry_count}</div>
      </dl>
      {run.error_details ? <p className="text-terracotta">{run.error_details}</p> : null}
      <pre className="overflow-auto rounded-2xl bg-ink/5 p-3 text-xs">{JSON.stringify(run.errors, null, 2)}</pre>
      <div className="flex gap-2">
        <button
          className="rounded-full bg-ink px-4 py-2 text-sm text-paper"
          onClick={async () => {
            setRun(await client.retryRun(run.id));
            setMessage("Retry queued");
          }}
        >
          Retry
        </button>
        <button
          className="rounded-full border border-ink/15 px-4 py-2 text-sm"
          disabled={!["queued", "running"].includes(run.status)}
          title={["queued", "running"].includes(run.status) ? "" : "Only queued or running jobs can be cancelled"}
          onClick={async () => {
            setRun(await client.cancelRun(run.id));
            setMessage("Cancel requested");
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
