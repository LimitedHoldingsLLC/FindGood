import type {
  Candidate,
  Deal,
  DealList,
  DealQuery,
  Snapshot,
  Source,
  Venue,
  VenueList,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let code: string | undefined;
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { error?: { code?: string; message?: string } };
      code = body.error?.code;
      message = body.error?.message ?? message;
    } catch {
      // Keep the generic message when the body is not JSON.
    }
    throw new ApiError(message, response.status, code);
  }
  return (await response.json()) as T;
}

function queryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  listDeals(query: DealQuery = {}): Promise<DealList> {
    return request(`/api/v1/deals${queryString({ ...query })}`);
  },
  getDeal(id: string): Promise<Deal> {
    return request(`/api/v1/deals/${id}`);
  },
  listVenues(query: { city?: string; neighborhood?: string; page?: number } = {}): Promise<VenueList> {
    return request(`/api/v1/venues${queryString(query)}`);
  },
  getVenue(slug: string): Promise<Venue> {
    return request(`/api/v1/venues/${slug}`);
  },
  flags(): Promise<{ flags: Record<string, boolean> }> {
    return request("/api/v1/flags");
  },
};

export function adminApi(key: string) {
  const headers = { "X-Admin-Key": key };
  return {
    login: (apiKey: string) =>
      request<{ ok: boolean }>("/api/v1/admin/session", {
        method: "POST",
        body: JSON.stringify({ api_key: apiKey }),
      }),
    venues: () => request<Venue[]>("/api/v1/admin/venues", { headers }),
    createVenue: (body: object) =>
      request<Venue>("/api/v1/admin/venues", { method: "POST", headers, body: JSON.stringify(body) }),
    updateVenue: (id: string, body: object) =>
      request<Venue>(`/api/v1/admin/venues/${id}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(body),
      }),
    addLocation: (venueId: string, body: object) =>
      request<Venue>(`/api/v1/admin/venues/${venueId}/locations`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      }),
    deals: () => request<Deal[]>("/api/v1/admin/deals", { headers }),
    createDeal: (body: object) =>
      request<Deal>("/api/v1/admin/deals", { method: "POST", headers, body: JSON.stringify(body) }),
    updateDeal: (id: string, body: object) =>
      request<Deal>(`/api/v1/admin/deals/${id}`, { method: "PATCH", headers, body: JSON.stringify(body) }),
    sources: () => request<Source[]>("/api/v1/admin/sources", { headers }),
    createSource: (body: object) =>
      request<Source>("/api/v1/admin/sources", { method: "POST", headers, body: JSON.stringify(body) }),
    disableSource: (id: string) =>
      request<Source>(`/api/v1/admin/sources/${id}/disable`, { method: "POST", headers }),
    refreshSource: (id: string) =>
      request(`/api/v1/admin/sources/${id}/refresh/sync`, { method: "POST", headers }),
    snapshots: (sourceId: string) =>
      request<Snapshot[]>(`/api/v1/admin/sources/${sourceId}/snapshots`, { headers }),
    candidates: (reviewStatus?: string) =>
      request<Candidate[]>(
        `/api/v1/admin/candidates${reviewStatus ? `?review_status=${reviewStatus}` : ""}`,
        { headers },
      ),
    approveCandidate: (id: string) =>
      request<Deal>(`/api/v1/admin/candidates/${id}/approve`, { method: "POST", headers }),
    rejectCandidate: (id: string) =>
      request<Candidate>(`/api/v1/admin/candidates/${id}/reject`, { method: "POST", headers }),
  };
}

export { API_BASE };
