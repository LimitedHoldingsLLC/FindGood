"use client";

import { useEffect, useState } from "react";

import { Pill, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminProvider, AdminRun } from "@/lib/api/types";

export default function ProvidersPage() {
  const client = useAdminClient();
  const [providers, setProviders] = useState<AdminProvider[]>([]);
  const [city, setCity] = useState("Los Angeles");
  const [message, setMessage] = useState<string | null>(null);
  const [run, setRun] = useState<AdminRun | null>(null);

  useEffect(() => {
    if (!client) return;
    void client.providers().then(setProviders);
  }, [client, run?.status]);

  if (!client) return null;
  const api = client;

  async function search(kind: "google" | "yelp" | "tripadvisor") {
    setMessage(null);
    try {
      const next =
        kind === "google"
          ? await api.googleSearch({ city, sync: false })
          : kind === "yelp"
            ? await api.yelpSearch({ city, sync: false })
            : await api.tripadvisorSearch({ city, sync: false });
      setRun(next);
      setMessage(`Queued ${kind} search in ${city}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Provider call failed");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Providers</h1>
      <p className="text-sm text-muted">
        API keys are never shown. Discovery calls cost money at Google and may count against Yelp and Tripadvisor
        limits.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {providers.map((provider) => (
          <section key={provider.name} className="rounded-2xl border border-ink/10 bg-card p-5">
            <div className="flex items-center justify-between">
              <h2 className="font-medium capitalize">{provider.name.replace("_", " ")}</h2>
              <Pill label={provider.configured ? "configured" : "not configured"} tone={provider.configured ? "good" : "warn"} />
            </div>
            <dl className="mt-3 space-y-1 text-sm text-muted">
              <div>Calls today: {provider.calls_today}</div>
              <div>Errors today: {provider.errors_today}</div>
              <div>Imported today: {provider.records_imported_today}</div>
              <div>Last status: {provider.last_status ?? "never"}</div>
            </dl>
            {provider.note ? <p className="mt-2 text-xs text-muted">{provider.note}</p> : null}
          </section>
        ))}
      </div>
      <form className="flex flex-wrap gap-2" onSubmit={(e) => e.preventDefault()}>
        <input className="rounded-lg border border-ink/15 px-3 py-2" value={city} onChange={(e) => setCity(e.target.value)} />
        <button className="rounded-lg bg-ink px-3 py-2 text-paper" type="button" onClick={() => search("google")}>
          Run Google discovery
        </button>
        <button className="rounded-lg border border-ink/15 px-3 py-2" type="button" onClick={() => search("yelp")}>
          Run Yelp discovery
        </button>
        <button className="rounded-lg border border-ink/15 px-3 py-2" type="button" onClick={() => search("tripadvisor")}>
          Run Tripadvisor discovery
        </button>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
      {run ? <p className="text-sm text-muted">Run {run.id} · {run.status}</p> : null}
    </div>
  );
}
