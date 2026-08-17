"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Candidate, Deal, Snapshot, Source, Venue } from "@/lib/api/types";
import { useAdminClient } from "@/features/admin/AdminShell";

export default function CatalogPage() {
  const client = useAdminClient();
  const [venues, setVenues] = useState<Venue[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [venueName, setVenueName] = useState("");
  const [dealTitle, setDealTitle] = useState("");
  const [dealLocationId, setDealLocationId] = useState("");

  useEffect(() => {
    if (!client) return;
    Promise.all([client.venues(), client.deals(), client.sources(), client.candidates()]).then(
      ([nextVenues, nextDeals, nextSources, nextCandidates]) => {
        setVenues(nextVenues);
        setDeals(nextDeals);
        setSources(nextSources);
        setCandidates(nextCandidates);
        const firstLocation = nextVenues[0]?.locations[0]?.id;
        if (firstLocation) setDealLocationId(firstLocation);
      },
    );
  }, [client]);

  if (!client) return null;
  const api = client;

  async function refreshAll() {
    const [nextVenues, nextDeals, nextSources, nextCandidates] = await Promise.all([
      api.venues(),
      api.deals(),
      api.sources(),
      api.candidates(),
    ]);
    setVenues(nextVenues);
    setDeals(nextDeals);
    setSources(nextSources);
    setCandidates(nextCandidates);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl">Catalog</h1>
        <p className="text-sm text-muted">Manual venue and deal entry. Seed data is fictional.</p>
        {message ? <p className="mt-2 text-sm text-forest">{message}</p> : null}
      </div>
      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Create venue</h2>
        <form
          className="mt-3 flex flex-wrap gap-2"
          onSubmit={async (event) => {
            event.preventDefault();
            await api.createVenue({ name: venueName, primary_category: "restaurant" });
            setVenueName("");
            setMessage("Venue created");
            await refreshAll();
          }}
        >
          <input
            className="rounded-lg border border-ink/15 px-3 py-2"
            placeholder="Venue name"
            value={venueName}
            onChange={(event) => setVenueName(event.target.value)}
          />
          <button className="rounded-lg bg-ink px-3 py-2 text-paper">Save</button>
        </form>
      </section>
      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Create deal</h2>
        <form
          className="mt-3 flex flex-wrap gap-2"
          onSubmit={async (event) => {
            event.preventDefault();
            await api.createDeal({
              venue_location_id: dealLocationId,
              title: dealTitle,
              deal_type: "happy_hour",
              offering_kind: "both",
              schedules: [{ days_of_week: [1, 2, 3, 4, 5], start_time: "15:00", end_time: "18:00" }],
              items: [{ name: "House special", normal_price: "16.00", deal_price: "9.00" }],
            });
            setDealTitle("");
            setMessage("Deal created");
            await refreshAll();
          }}
        >
          <select
            className="rounded-lg border border-ink/15 px-3 py-2"
            value={dealLocationId}
            onChange={(event) => setDealLocationId(event.target.value)}
          >
            {venues.flatMap((venue) =>
              venue.locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {venue.name} — {location.neighborhood}
                </option>
              )),
            )}
          </select>
          <input
            className="rounded-lg border border-ink/15 px-3 py-2"
            placeholder="Deal title"
            value={dealTitle}
            onChange={(event) => setDealTitle(event.target.value)}
          />
          <button className="rounded-lg bg-ink px-3 py-2 text-paper">Save</button>
        </form>
      </section>
      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Sources</h2>
        <ul className="mt-3 space-y-3 text-sm">
          {sources.map((source) => (
            <li key={source.id} className="rounded-xl bg-paper p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {source.source_type} · {source.url}
                </span>
                <button
                  className="underline"
                  onClick={async () => {
                    await api.refreshSource(source.id);
                    setSnapshots(await api.snapshots(source.id));
                    setMessage(`Ingested ${source.url}`);
                  }}
                >
                  Refresh now
                </button>
              </div>
            </li>
          ))}
        </ul>
        {snapshots.map((snapshot) => (
          <pre key={snapshot.id} className="mt-2 overflow-auto text-xs">
            {snapshot.fetched_at} · {snapshot.content_hash.slice(0, 12)}
          </pre>
        ))}
      </section>
      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Candidates</h2>
        <ul className="mt-3 space-y-3 text-sm">
          {candidates.map((candidate) => (
            <li key={candidate.id} className="rounded-xl bg-paper p-3">
              <p>
                {(candidate.normalized_payload.title as string) ?? "Untitled"} · {candidate.review_status}
              </p>
              {candidate.review_status === "pending" ? (
                <div className="mt-2 flex gap-3">
                  <button
                    className="underline"
                    onClick={async () => {
                      await api.approveCandidate(candidate.id);
                      await refreshAll();
                    }}
                  >
                    Approve / publish
                  </button>
                  <button
                    className="underline"
                    onClick={async () => {
                      await api.rejectCandidate(candidate.id);
                      await refreshAll();
                    }}
                  >
                    Reject
                  </button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
      <p className="text-sm text-muted">
        {deals.length} deals in catalog. Public pages:{" "}
        {venues.slice(0, 3).map((venue) => (
          <Link key={venue.id} className="mr-2 underline" href={`/venues/${venue.slug}`}>
            {venue.name}
          </Link>
        ))}
      </p>
    </div>
  );
}
