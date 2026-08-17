"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Pill, runTone, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminRun, CrawlDomain } from "@/lib/api/types";

export default function CrawlerPage() {
  const client = useAdminClient();
  const [url, setUrl] = useState("");
  const [run, setRun] = useState<AdminRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<AdminRun[]>([]);
  const [domains, setDomains] = useState<CrawlDomain[]>([]);

  useEffect(() => {
    if (!client) return;
    void client.runs({ provider: "website_crawler", page_size: 10 }).then((page) => setRecent(page.items));
    void client.crawlDomains().then(setDomains);
  }, [client, run?.id, run?.status]);

  useEffect(() => {
    if (!client || !run || !["queued", "running"].includes(run.status)) return;
    const timer = setInterval(async () => setRun(await client.run(run.id)), 3000);
    return () => clearInterval(timer);
  }, [client, run]);

  if (!client) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-4xl">Crawler</h1>
        <p className="text-sm text-muted">
          Manual crawls still honor robots.txt, SSRF protection, rate limits, and page caps. They never bypass
          safety rules.
        </p>
      </div>
      <form
        className="flex flex-wrap gap-2 rounded-2xl border border-ink/10 bg-card p-5"
        onSubmit={async (event) => {
          event.preventDefault();
          setError(null);
          try {
            setRun(await client.crawl({ url, sync: false }));
          } catch (err) {
            setError(err instanceof Error ? err.message : "Crawl failed");
          }
        }}
      >
        <input
          className="min-w-[240px] flex-1 rounded-lg border border-ink/15 px-3 py-2"
          placeholder="https://restaurant.example/happy-hour"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          required
        />
        <button className="rounded-lg bg-ink px-4 py-2 text-paper">Queue crawl</button>
      </form>
      {error ? <p className="text-sm text-terracotta">{error}</p> : null}
      {run ? (
        <section className="rounded-2xl border border-ink/10 bg-card p-5 text-sm">
          <div className="flex items-center gap-2">
            <Pill label={run.status} tone={runTone(run.status)} />
            <Link className="underline" href={`/admin/runs/${run.id}`}>
              {run.id}
            </Link>
          </div>
          <dl className="mt-3 grid gap-1 sm:grid-cols-2">
            <div>Pages discovered {run.pages_discovered}</div>
            <div>Pages fetched {run.pages_fetched}</div>
            <div>Skipped {run.pages_skipped}</div>
            <div>Robots blocked {run.robots_blocked}</div>
            <div>Offers found {run.offers_discovered}</div>
            <div>Offers created {run.offers_created}</div>
          </dl>
          {run.error_details ? <p className="mt-2 text-terracotta">{run.error_details}</p> : null}
        </section>
      ) : null}
      <section>
        <h2 className="font-medium">Recent crawls</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {recent.map((item) => (
            <li key={item.id} className="flex flex-wrap justify-between gap-2 rounded-xl bg-card p-3">
              <Link className="underline" href={`/admin/runs/${item.id}`}>
                {item.target_url ?? item.id}
              </Link>
              <Pill label={item.status} tone={runTone(item.status)} />
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="font-medium">Domain health</h2>
        <p className="mt-1 text-sm text-muted">
          Hosts that keep failing are slowed down automatically so we do not hammer a dead website.
        </p>
        <ul className="mt-3 space-y-2 text-sm">
          {domains.length === 0 ? <li className="text-muted">No crawls recorded yet.</li> : null}
          {domains.map((domain) => (
            <li key={domain.host} className="rounded-xl bg-card p-3">
              <div className="flex flex-wrap justify-between gap-2">
                <strong>{domain.host}</strong>
                <span>
                  {domain.consecutive_failures > 0
                    ? `${domain.consecutive_failures} consecutive failures`
                    : `${domain.success_count} successful fetches`}
                </span>
              </div>
              <div className="mt-1 text-muted">
                robots {domain.robots_status ?? "unknown"} · last HTTP {domain.last_http_status ?? "—"}
                {domain.last_error ? ` · ${domain.last_error}` : ""}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
