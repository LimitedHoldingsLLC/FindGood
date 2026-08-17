// Mirrors the public FastAPI contract. Required fields are locked by
// services/backend/tests/contract/test_consumer_api.py. Additive API fields
// are allowed; removals or renames must update this file in the same change.
export type AvailabilityStatus =
  | "active_now"
  | "starts_soon"
  | "active_later_today"
  | "ended_today"
  | "currently_unavailable";

export type OfferingKind = "food" | "drink" | "both";

export type Vertical =
  | "food"
  | "beauty"
  | "fitness"
  | "entertainment"
  | "activities"
  | "retail"
  | "services"
  | "health"
  | "travel"
  | "other";

export const FOOD_VERTICAL: Vertical = "food";

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
}

export interface Availability {
  status: AvailabilityStatus;
  timezone: string;
  local_time: string;
  ends_at: string | null;
  next_occurrence: string | null;
  label: string;
}

export interface Verification {
  verification_type: string;
  verified_at: string | null;
  actor: string | null;
  label: string;
  days_ago: number | null;
  is_fresh: boolean;
}

export interface Provenance {
  source_type: string | null;
  source_url: string | null;
  snapshot_id: string | null;
  published_by: string | null;
  published_at: string | null;
}

export interface DealItem {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  normal_price: string | null;
  deal_price: string | null;
  currency: string;
  absolute_savings: string | null;
  percent_savings: string | null;
}

export interface DealSchedule {
  id: string;
  days_of_week: number[];
  start_time: string | null;
  end_time: string | null;
  ends_at_close: boolean;
  valid_from: string | null;
  valid_until: string | null;
}

export interface VenueCard {
  id: string;
  name: string;
  slug: string;
  primary_category: string;
  vertical: Vertical;
  neighborhood: string | null;
  city: string;
  timezone: string;
}

export interface Location {
  id: string;
  label: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  region: string;
  postal_code: string;
  neighborhood: string | null;
  latitude: string;
  longitude: string;
  timezone: string;
}

export interface DealScore {
  score: number;
  factors: { name: string; contribution: number; explanation: string }[];
}

export interface Deal {
  id: string;
  title: string;
  description: string | null;
  deal_type: string;
  offering_kind: OfferingKind;
  vertical: Vertical;
  source_confidence: string;
  venue: VenueCard;
  location: Location;
  items: DealItem[];
  schedules: DealSchedule[];
  availability: Availability;
  verification: Verification;
  provenance: Provenance | null;
  score: DealScore | null;
  distance_km: number | null;
}

export interface Venue {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  website_url: string | null;
  phone: string | null;
  primary_category: string;
  vertical: Vertical;
  status: string;
  locations: Location[];
  current_deals: Deal[];
  upcoming_deals: Deal[];
}

export interface DealList {
  items: Deal[];
  pagination: Pagination;
}

export interface VenueList {
  items: Venue[];
  pagination: Pagination;
}

export interface Source {
  id: string;
  venue_id: string | null;
  source_type: string;
  url: string;
  canonical_identity: string;
  is_active: boolean;
  crawl_enabled: boolean;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_error: string | null;
  trust_level: string;
}

export interface Snapshot {
  id: string;
  source_id: string;
  crawl_run_id: string | null;
  fetched_at: string;
  http_status: number | null;
  content_type: string | null;
  content_hash: string;
  storage_ref: string | null;
  parser_version: string | null;
  extra_metadata: Record<string, unknown>;
  raw_content: string | null;
}

export interface Candidate {
  id: string;
  source_snapshot_id: string;
  crawl_run_id: string | null;
  candidate_type: string;
  payload: Record<string, unknown>;
  normalized_payload: Record<string, unknown>;
  validation_status: string;
  validation_errors: unknown[];
  review_status: string;
  published_deal_id: string | null;
  confidence: string;
  diagnostic_notes: string | null;
}

export interface AdminSession {
  ok: boolean;
  subject: string;
  token: string;
  expires_at: string;
}

export interface DealQuery {
  city?: string;
  neighborhood?: string;
  category?: string;
  food_or_drink?: OfferingKind;
  deal_type?: string;
  max_price?: string;
  latitude?: string;
  longitude?: string;
  radius?: string;
  active_now?: boolean;
  vertical?: Vertical;
  page?: number;
  page_size?: number;
}
