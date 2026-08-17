"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { BrandMark } from "@/components/layout/BrandMark";
import { adminApi } from "@/lib/api/client";
import { clearAdminToken, getAdminToken } from "@/features/admin/admin-session";

const NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/venues", label: "Businesses" },
  { href: "/admin/deals", label: "Offers" },
  { href: "/admin/crawler", label: "Crawler" },
  { href: "/admin/providers", label: "Providers" },
  { href: "/admin/runs", label: "Ingestion runs" },
  { href: "/admin/freshness", label: "Data freshness" },
  { href: "/admin/review", label: "Review queue" },
  { href: "/admin/errors", label: "Errors" },
  { href: "/admin/jobs", label: "Jobs" },
  { href: "/admin/health", label: "System health" },
  { href: "/admin/catalog", label: "Catalog" },
  { href: "/admin/settings", label: "Settings" },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const [token, setToken] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [searchHits, setSearchHits] = useState<string | null>(null);

  useEffect(() => {
    if (path === "/admin/login") return;
    const stored = getAdminToken();
    if (!stored) {
      router.replace("/admin/login");
      return;
    }
    setToken(stored);
  }, [path, router]);

  const client = useMemo(() => (token ? adminApi(token) : null), [token]);

  if (path === "/admin/login") return <>{children}</>;
  if (!token) return <p className="p-8 text-sm text-muted">Checking admin session…</p>;

  return (
    <div className="min-h-screen bg-ink text-paper">
      <div className="flex min-h-screen">
        <aside className="hidden w-56 shrink-0 border-r border-paper/10 bg-ink md:block">
          <div className="px-4 py-5">
            <p className="font-display text-xl tracking-tight">
              <BrandMark accentClassName="text-gold" />
            </p>
            <p className="text-xs uppercase tracking-widest text-gold">Control plane</p>
          </div>
          <nav className="space-y-0.5 px-2 pb-8">
            {NAV.map((item) => {
              const active = path === item.href || (item.href !== "/admin" && path.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-lg px-3 py-2 text-sm ${
                    active ? "bg-paper/10 text-paper" : "text-paper/70 hover:bg-paper/5 hover:text-paper"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <div className="flex min-w-0 flex-1 flex-col bg-paper text-ink">
          <header className="flex flex-wrap items-center gap-3 border-b border-ink/10 bg-card px-4 py-3">
            <form
              className="min-w-[220px] flex-1"
              onSubmit={async (event) => {
                event.preventDefault();
                if (!client || !query.trim()) return;
                const result = await client.search(query.trim());
                setSearchHits(
                  `${result.venues.length} businesses, ${result.deals.length} offers, ${result.runs.length} runs`,
                );
                if (result.venues[0]) router.push(`/admin/venues/${result.venues[0].id}`);
                else if (result.deals[0]) router.push(`/admin/deals/${result.deals[0].id}`);
                else if (result.runs[0]) router.push(`/admin/runs/${result.runs[0].id}`);
              }}
            >
              <input
                className="w-full rounded-full border border-ink/15 bg-paper px-4 py-2 text-sm"
                placeholder="Search name, phone, domain, run ID…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </form>
            {searchHits ? <p className="text-xs text-muted">{searchHits}</p> : null}
            <button
              className="rounded-full border border-ink/15 px-3 py-1.5 text-sm"
              type="button"
              onClick={() => {
                clearAdminToken();
                router.replace("/admin/login");
              }}
            >
              Sign out
            </button>
          </header>
          <div className="flex-1 px-4 py-6 md:px-8">{children}</div>
        </div>
      </div>
    </div>
  );
}

export function useAdminClient() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => {
    const stored = getAdminToken();
    if (!stored) {
      router.replace("/admin/login");
      return;
    }
    setToken(stored);
  }, [router]);
  return useMemo(() => (token ? adminApi(token) : null), [token]);
}

export function Pill({ label, tone = "neutral" }: { label: string; tone?: "good" | "warn" | "bad" | "neutral" }) {
  const styles = {
    good: "bg-forest text-paper",
    warn: "bg-gold/25 text-ink",
    bad: "bg-terracotta text-paper",
    neutral: "bg-ink/10 text-ink",
  }[tone];
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}>{label}</span>;
}

export function freshnessTone(status: string): "good" | "warn" | "bad" | "neutral" {
  if (status === "fresh") return "good";
  if (status === "aging" || status === "unverified") return "warn";
  if (status === "stale" || status === "expired" || status === "verification_failed") return "bad";
  return "neutral";
}

export function runTone(status: string): "good" | "warn" | "bad" | "neutral" {
  if (status === "completed" || status === "succeeded") return "good";
  if (status === "running" || status === "queued" || status === "partial") return "warn";
  if (status === "failed") return "bad";
  return "neutral";
}
