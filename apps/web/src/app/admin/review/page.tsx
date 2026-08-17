"use client";

import { useEffect, useState } from "react";

import { Pill, useAdminClient } from "@/features/admin/AdminShell";
import type { AdminReview } from "@/lib/api/types";

export default function ReviewPage() {
  const client = useAdminClient();
  const [items, setItems] = useState<AdminReview[]>([]);

  async function load() {
    if (!client) return;
    const page = await client.review({ status: "pending", page_size: 30 });
    setItems(page.items);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Review queue</h1>
      <p className="text-sm text-muted">Ambiguous extracts and possible duplicates wait here. High-risk merges are never automatic.</p>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-2xl border border-ink/10 bg-card p-5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-medium">{item.title}</h2>
              <Pill label={item.reason} />
            </div>
            <p className="mt-2 text-sm">{item.explanation}</p>
            {item.suggested_action ? <p className="mt-1 text-sm text-muted">Suggested: {item.suggested_action}</p> : null}
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              {["approve", "reject", "ignore", "recheck"].map((action) => (
                <button
                  key={action}
                  className="rounded-full border border-ink/15 px-3 py-1 capitalize"
                  onClick={async () => {
                    await client.reviewAction(item.id, action);
                    await load();
                  }}
                >
                  {action}
                </button>
              ))}
            </div>
          </li>
        ))}
        {items.length === 0 ? <p className="text-sm text-muted">Nothing waiting.</p> : null}
      </ul>
    </div>
  );
}
