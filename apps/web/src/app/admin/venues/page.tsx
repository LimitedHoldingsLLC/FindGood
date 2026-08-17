"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, freshnessTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminVenue } from "@/lib/api/types";

export default function AdminVenuesPage() {
  const client = useAdminClient();
  const [items, setItems] = useState<AdminVenue[]>([]);
  const [q, setQ] = useState("");
  const [total, setTotal] = useState(0);

  async function load(query = q) {
    if (!client) return;
    const page = await client.opsVenues({ q: query || undefined, page: 1, page_size: 30 });
    setItems(page.items);
    setTotal(page.total);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Businesses</h1>
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void load();
        }}
      >
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Name, phone, website"
          value={q}
          onChange={(event) => setQ(event.target.value)}
        />
        <button className="rounded-lg bg-ink px-3 py-2 text-paper">Search</button>
      </form>
      <p className="text-sm text-muted">{total} businesses</p>
      <div className="overflow-x-auto rounded-2xl border border-ink/10 bg-card">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-xs uppercase text-muted">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">City</th>
              <th className="px-3 py-2">Freshness</th>
              <th className="px-3 py-2">Providers</th>
            </tr>
          </thead>
          <tbody>
            {items.map((venue) => (
              <tr key={venue.id} className="border-t border-ink/10">
                <td className="px-3 py-2">
                  <Link className="underline" href={`/admin/venues/${venue.id}`}>
                    {venue.name}
                  </Link>
                </td>
                <td className="px-3 py-2">{venue.city}</td>
                <td className="px-3 py-2">
                  <Pill label={venue.freshness_status} tone={freshnessTone(venue.freshness_status)} />
                </td>
                <td className="px-3 py-2 text-muted">{venue.provider_links.map((l) => l.provider).join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
