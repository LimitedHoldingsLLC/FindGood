"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { adminApi } from "@/lib/api/client";
import type { Candidate, Deal, Snapshot, Source, Venue } from "@/lib/api/types";
import { getAdminKey } from "@/features/admin/admin-session";

export default function AdminHomePage() {
  const router = useRouter();
  const [key, setKey] = useState<string | null>(null);
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
    const stored = getAdminKey();
    if (!stored) {
      router.replace("/admin/login");
      return;
    }
    setKey(stored);
    const client = adminApi(stored);
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
  }, [router]);

  if (!key) return <p>Checking admin session…</p>;
  const client = adminApi(key);

  async function refreshAll() {
    const [nextVenues, nextDeals, nextSources, nextCandidates] = await Promise.all([
      client.venues(),
      client.deals(),
      client.sources(),
      client.candidates(),
    ]);
    setVenues(nextVenues);
    setDeals(nextDeals);
    setSources(nextSources);
    setCandidates(nextCandidates);
  }

  return (
    <div className="space-y-10">
      <div>
        <h1 className="font-display text-4xl">Curate</h1>
        <p className="text-sm text-muted">Reliability over polish. Seed data is fictional.</p>
        {message ? <p className="mt-2 text-sm text-forest">{message}</p> : null}
      </div>

      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Create venue</h2>
        <form
          className="mt-3 flex flex-wrap gap-2"
          onSubmit={async (event) => {
            event.preventDefault();
            await client.createVenue({ name: venueName, primary_category: "restaurant" });
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
        <ul className="mt-4 space-y-1 text-sm">
          {venues.map((venue) => (
            <li key={venue.id}>
              <Link className="underline" href={`/venues/${venue.slug}`}>
                {venue.name}
              </Link>{" "}
              <span className="text-muted">{venue.locations[0]?.neighborhood}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Create deal</h2>
        <form
          className="mt-3 flex flex-wrap gap-2"
          onSubmit={async (event) => {
            event.preventDefault();
            await client.createDeal({
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
        <ul className="mt-4 space-y-1 text-sm">
          {deals.map((deal) => (
            <li key={deal.id}>
              {deal.title} · {deal.venue.name} · {deal.availability.status}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Sources</h2>
        <ul className="mt-3 space-y-3 text-sm">
          {sources.map((source) => (
            <li key={source.id} className="rounded-xl bg-paper p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {source.source_type} · {source.url} · {source.is_active ? "active" : "disabled"}
                </span>
                <div className="flex gap-2">
                  <button
                    className="underline"
                    onClick={async () => {
                      await client.refreshSource(source.id);
                      setMessage(`Ingested ${source.url}`);
                      const next = await client.snapshots(source.id);
                      setSnapshots(next);
                      await refreshAll();
                    }}
                  >
                    Refresh now
                  </button>
                  <button
                    className="underline"
                    onClick={async () => {
                      await client.disableSource(source.id);
                      await refreshAll();
                    }}
                  >
                    Disable
                  </button>
                  <button
                    className="underline"
                    onClick={async () => setSnapshots(await client.snapshots(source.id))}
                  >
                    Snapshots
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
        {snapshots.length > 0 ? (
          <div className="mt-4 rounded-xl bg-ink/5 p-3 text-xs">
            <p className="font-medium">Latest snapshots</p>
            {snapshots.map((snapshot) => (
              <pre key={snapshot.id} className="mt-2 overflow-auto whitespace-pre-wrap">
                {snapshot.fetched_at} · {snapshot.content_hash.slice(0, 12)} · status {snapshot.http_status}
                {"\n"}
                {snapshot.raw_content?.slice(0, 400)}
              </pre>
            ))}
          </div>
        ) : null}
      </section>

      <section className="rounded-2xl border border-ink/10 bg-card p-5">
        <h2 className="font-medium">Candidates</h2>
        <ul className="mt-3 space-y-3 text-sm">
          {candidates.map((candidate) => (
            <li key={candidate.id} className="rounded-xl bg-paper p-3">
              <p>
                {(candidate.normalized_payload.title as string) ?? "Untitled"} · {candidate.review_status} ·{" "}
                {candidate.validation_status}
              </p>
              <p className="text-muted">{candidate.diagnostic_notes}</p>
              {candidate.review_status === "pending" ? (
                <div className="mt-2 flex gap-3">
                  <button
                    className="underline"
                    onClick={async () => {
                      await client.approveCandidate(candidate.id);
                      setMessage("Candidate published");
                      await refreshAll();
                    }}
                  >
                    Approve / publish
                  </button>
                  <button
                    className="underline"
                    onClick={async () => {
                      await client.rejectCandidate(candidate.id);
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
    </div>
  );
}
