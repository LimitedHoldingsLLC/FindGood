"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { adminApi } from "@/lib/api/client";
import { setAdminKey } from "@/features/admin/admin-session";

export default function AdminLoginPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await adminApi(apiKey).login(apiKey);
      setAdminKey(apiKey);
      router.push("/admin");
    } catch {
      setError("That key wasn’t accepted.");
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-md rounded-3xl border border-ink/10 bg-card p-6">
      <h1 className="font-display text-3xl">Admin</h1>
      <p className="mt-2 text-sm text-muted">Internal only. Use ADMIN_API_KEY from your environment.</p>
      <label className="mt-6 block text-sm">
        Admin key
        <input
          className="mt-1 w-full rounded-xl border border-ink/15 bg-paper px-3 py-2"
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
        />
      </label>
      {error ? <p className="mt-3 text-sm text-terracotta">{error}</p> : null}
      <button className="mt-5 rounded-full bg-ink px-4 py-2 text-paper" type="submit">
        Continue
      </button>
    </form>
  );
}
