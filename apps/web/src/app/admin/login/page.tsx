"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { createAdminSession, ApiError } from "@/lib/api/client";
import { setAdminToken } from "@/features/admin/admin-session";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const session = await createAdminSession(username, password);
      setAdminToken(session.token);
      router.push("/admin");
    } catch (error) {
      if (error instanceof ApiError && error.code === "rate_limited") {
        setError("Too many sign-in attempts. Wait 15 minutes and try again.");
      } else {
        setError("That username or password wasn’t accepted.");
      }
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-md rounded-3xl border border-ink/10 bg-card p-6">
      <h1 className="font-display text-3xl">Admin</h1>
      <p className="mt-2 text-sm text-muted">Internal only. Sign in with your admin username and password.</p>
      <label className="mt-6 block text-sm">
        Username
        <input
          autoComplete="username"
          className="mt-1 w-full rounded-xl border border-ink/15 bg-paper px-3 py-2"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
      </label>
      <label className="mt-4 block text-sm">
        Password
        <input
          autoComplete="current-password"
          className="mt-1 w-full rounded-xl border border-ink/15 bg-paper px-3 py-2"
          required
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      {error ? <p className="mt-3 text-sm text-terracotta">{error}</p> : null}
      <button className="mt-5 rounded-full bg-ink px-4 py-2 text-paper" type="submit">
        Sign in
      </button>
    </form>
  );
}
