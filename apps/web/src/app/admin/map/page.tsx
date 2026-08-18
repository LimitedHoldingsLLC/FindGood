"use client";

import { useEffect, useState } from "react";

import { Pill, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminMapQuality } from "@/lib/api/types";

export default function AdminMapPage() {
  const client = useAdminClient();
  const [data, setData] = useState<AdminMapQuality | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!client) return;
    void client.mapQuality().then(setData);
  }, [client]);

  if (!client || !data) return <p className="text-sm text-muted">Loading map quality…</p>;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Map quality</h1>
      <p className="text-sm text-muted">
        FindGood coordinates decide who appears on the consumer map. A missing Google Place ID is not a problem.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Map eligible", data.map_eligible],
          ["Needs review", data.needs_review],
          ["Missing geocode source", data.missing_geocode_source],
          ["Geocodes today", data.geocodes_today],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-2xl border border-ink/10 bg-card p-4">
            <p className="text-xs uppercase tracking-widest text-muted">{label}</p>
            <p className="mt-2 font-display text-3xl">{value}</p>
          </div>
        ))}
      </div>
      <p className="text-sm">
        Geocoding: <Pill label={data.geocoding_configured ? "configured" : "not configured"} tone={data.geocoding_configured ? "good" : "warn"} />
      </p>
      {message ? <p className="text-sm text-forest">{message}</p> : null}
      <div className="space-y-3">
        {data.items.length === 0 ? <p className="text-sm text-muted">No locations currently need review.</p> : null}
        {data.items.map((item) => (
          <section key={item.id} className="rounded-2xl border border-ink/10 bg-card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-medium">{item.venue_name ?? "Unknown venue"}</h2>
              <Pill label={item.location_confidence} />
            </div>
            <p className="mt-1 text-sm text-muted">
              {item.address}, {item.city} · {item.latitude}, {item.longitude}
            </p>
            <p className="text-xs text-muted">
              Source {item.geocode_source ?? "unknown"} · {item.geocode_accuracy ?? "n/a"}
            </p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                className="rounded-full border border-ink/15 px-3 py-1.5 text-sm"
                onClick={async () => {
                  await client.updateLocationCoordinates(item.id, {
                    latitude: item.latitude,
                    longitude: item.longitude,
                    location_confidence: "verified",
                  });
                  setMessage("Marked verified");
                  setData(await client.mapQuality());
                }}
              >
                Mark verified
              </button>
              <button
                type="button"
                className="rounded-full border border-ink/15 px-3 py-1.5 text-sm"
                onClick={async () => {
                  await client.regeocodeLocation(item.id);
                  setMessage("Re-geocode queued");
                }}
              >
                Queue re-geocode
              </button>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
