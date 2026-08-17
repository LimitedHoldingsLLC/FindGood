"use client";

import { useEffect, useState } from "react";

import { useAdminClient } from "@/features/admin/AdminShell";
import type { AdminErrorGroup } from "@/lib/api/types";

export default function ErrorsPage() {
  const client = useAdminClient();
  const [groups, setGroups] = useState<AdminErrorGroup[]>([]);

  useEffect(() => {
    if (!client) return;
    void client.errors().then(setGroups);
  }, [client]);

  if (!client) return null;
  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Errors</h1>
      <p className="text-sm text-muted">Grouped from the last 7 days. This is not a raw log dump.</p>
      <ul className="space-y-3">
        {groups.map((group) => (
          <li key={`${group.category}-${group.provider}`} className="rounded-2xl border border-ink/10 bg-card p-4">
            <p className="font-medium">
              {group.category} {group.provider ? `· ${group.provider}` : ""}
            </p>
            <p className="text-sm text-muted">
              {group.count} times · first {group.first_at} · latest {group.latest_at}
            </p>
            <p className="mt-2 text-sm">{group.example}</p>
          </li>
        ))}
        {groups.length === 0 ? <p className="text-sm text-muted">No recorded errors this week.</p> : null}
      </ul>
    </div>
  );
}
