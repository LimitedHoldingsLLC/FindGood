import type {
  AdminAudit,
  AdminDeal,
  AdminErrorGroup,
  AdminFreshness,
  AdminOverview,
  AdminPage,
  AdminProvider,
  AdminReview,
  AdminRun,
  AdminSearch,
  AdminSession,
  AdminMapQuality,
  AdminSystem,
  AdminVenue,
  Candidate,
  CrawlDomain,
  Deal,
  DealList,
  DealQuery,
  Snapshot,
  Source,
  Venue,
  VenueList,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  (process.env.NODE_ENV === "production" ? "https://findgood.onrender.com" : "http://localhost:8000");

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
  listVenues(query: { city?: string; neighborhood?: string; category?: string; vertical?: string; page?: number } = {}): Promise<VenueList> {
    return request(`/api/v1/venues${queryString(query)}`);
  },
  getVenue(slug: string): Promise<Venue> {
    return request(`/api/v1/venues/${slug}`);
  },
  flags(): Promise<{ flags: Record<string, boolean> }> {
    return request("/api/v1/flags");
  },
  listMapLocations(
    query: Record<string, string | number | boolean | undefined>,
    init?: RequestInit,
  ): Promise<import("@/features/map/types").MapList> {
    return request(`/api/v1/map/locations${queryString(query)}`, init);
  },
};

export function createAdminSession(username: string, password: string) {
  return request<AdminSession>("/api/v1/admin/session", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function adminApi(token: string) {
  const headers = { Authorization: `Bearer ${token}` };
  return {
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
    overview: () => request<AdminOverview>("/api/v1/admin/overview", { headers }),
    search: (q: string) => request<AdminSearch>(`/api/v1/admin/search?q=${encodeURIComponent(q)}`, { headers }),
    opsVenues: (params: Record<string, string | number | undefined> = {}) =>
      request<AdminPage<AdminVenue>>(`/api/v1/admin/ops/venues${queryString(params)}`, { headers }),
    opsVenue: (id: string) => request<AdminVenue>(`/api/v1/admin/ops/venues/${id}`, { headers }),
    crawlVenue: (id: string) =>
      request<AdminRun>(`/api/v1/admin/ops/venues/${id}/crawl`, { method: "POST", headers, body: "{}" }),
    disableVenue: (id: string) =>
      request<AdminVenue>(`/api/v1/admin/ops/venues/${id}/disable`, { method: "POST", headers, body: "{}" }),
    refreshGoogle: (id: string) =>
      request<AdminRun>(`/api/v1/admin/ops/venues/${id}/refresh-google`, { method: "POST", headers, body: "{}" }),
    refreshYelp: (id: string) =>
      request<AdminRun>(`/api/v1/admin/ops/venues/${id}/refresh-yelp`, { method: "POST", headers, body: "{}" }),
    refreshTripadvisor: (id: string) =>
      request<AdminRun>(`/api/v1/admin/ops/venues/${id}/refresh-tripadvisor`, { method: "POST", headers, body: "{}" }),
    opsDeals: (params: Record<string, string | number | undefined> = {}) =>
      request<AdminPage<AdminDeal>>(`/api/v1/admin/ops/deals${queryString(params)}`, { headers }),
    opsDeal: (id: string) => request<AdminDeal>(`/api/v1/admin/ops/deals/${id}`, { headers }),
    verifyDeal: (id: string, notes?: string) =>
      request<AdminDeal>(`/api/v1/admin/ops/deals/${id}/verify`, {
        method: "POST",
        headers,
        body: JSON.stringify({ notes }),
      }),
    rejectDeal: (id: string) =>
      request<AdminDeal>(`/api/v1/admin/ops/deals/${id}/reject`, { method: "POST", headers, body: "{}" }),
    expireDeal: (id: string) =>
      request<AdminDeal>(`/api/v1/admin/ops/deals/${id}/expire`, { method: "POST", headers, body: "{}" }),
    restoreDeal: (id: string) =>
      request<AdminDeal>(`/api/v1/admin/ops/deals/${id}/restore`, { method: "POST", headers, body: "{}" }),
    crawl: (body: object) =>
      request<AdminRun>("/api/v1/admin/ingestion/crawl", { method: "POST", headers, body: JSON.stringify(body) }),
    googleSearch: (body: object) =>
      request<AdminRun>("/api/v1/admin/ingestion/google/search", {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      }),
    yelpSearch: (body: object) =>
      request<AdminRun>("/api/v1/admin/ingestion/yelp/search", {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      }),
    tripadvisorSearch: (body: object) =>
      request<AdminRun>("/api/v1/admin/ingestion/tripadvisor/search", {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      }),
    runs: (params: Record<string, string | number | undefined> = {}) =>
      request<AdminPage<AdminRun>>(`/api/v1/admin/ingestion/runs${queryString(params)}`, { headers }),
    run: (id: string) => request<AdminRun>(`/api/v1/admin/ingestion/runs/${id}`, { headers }),
    retryRun: (id: string) =>
      request<AdminRun>(`/api/v1/admin/ingestion/runs/${id}/retry`, { method: "POST", headers, body: "{}" }),
    cancelRun: (id: string) =>
      request<AdminRun>(`/api/v1/admin/ingestion/runs/${id}/cancel`, { method: "POST", headers, body: "{}" }),
    providers: () => request<AdminProvider[]>("/api/v1/admin/providers", { headers }),
    freshness: (params: Record<string, string | number | undefined> = {}) =>
      request<AdminFreshness>(`/api/v1/admin/freshness${queryString(params)}`, { headers }),
    queueStale: () =>
      request<{ queued: number }>("/api/v1/admin/freshness/queue-refresh", { method: "POST", headers, body: "{}" }),
    review: (params: Record<string, string | number | undefined> = {}) =>
      request<AdminPage<AdminReview>>(`/api/v1/admin/review${queryString(params)}`, { headers }),
    reviewAction: (id: string, action: string) =>
      request<AdminReview>(`/api/v1/admin/review/${id}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ action }),
      }),
    errors: () => request<AdminErrorGroup[]>("/api/v1/admin/errors", { headers }),
    crawlDomains: () => request<CrawlDomain[]>("/api/v1/admin/crawler/domains", { headers }),
    system: () => request<AdminSystem>("/api/v1/admin/system", { headers }),
    mapQuality: () => request<AdminMapQuality>("/api/v1/admin/map/quality", { headers }),
    updateLocationCoordinates: (id: string, body: object) =>
      request<Record<string, string>>(`/api/v1/admin/ops/locations/${id}/coordinates`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(body),
      }),
    regeocodeLocation: (id: string) =>
      request<{ job_id: string }>(`/api/v1/admin/ops/locations/${id}/re-geocode`, {
        method: "POST",
        headers,
        body: "{}",
      }),
    audit: () => request<AdminAudit[]>("/api/v1/admin/audit", { headers }),
    bulkCrawl: (venueIds: string[], confirm: boolean) =>
      request<{ queued: number; needs_confirmation?: boolean }>("/api/v1/admin/bulk/crawl", {
        method: "POST",
        headers,
        body: JSON.stringify({ venue_ids: venueIds, confirm }),
      }),
  };
}

export { API_BASE };
