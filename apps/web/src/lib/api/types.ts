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
  cuisines?: string[];
  price_level?: number | null;
  drink_kinds?: string[];
  accepts_reservations?: boolean;
  features?: string[];
  rating?: string | null;
  rating_review_count?: number;
  rating_source_count?: number;
  rating_providers?: string[];
  provider_ratings?: ProviderRating[];
}

export interface ProviderRating {
  provider: string;
  rating: string | null;
  review_count: number | null;
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
  freshness_status?: string | null;
  last_seen_at?: string | null;
  last_verified_at?: string | null;
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
  cuisines?: string[];
  price_level?: number | null;
  drink_kinds?: string[];
  accepts_reservations?: boolean;
  features?: string[];
  rating?: string | null;
  rating_review_count?: number;
  rating_source_count?: number;
  rating_providers?: string[];
  provider_ratings?: ProviderRating[];
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

export interface AdminPage<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface AdminOverview {
  system_working: boolean;
  freshness_health_percent: number;
  total_businesses: number;
  active_businesses: number;
  businesses_added_24h: number;
  businesses_added_7d: number;
  total_active_offers: number;
  offers_added_24h: number;
  offers_added_7d: number;
  verified_offers: number;
  stale_offers: number;
  expired_offers: number;
  unverified_offers: number;
  aging_offers: number;
  businesses_needing_refresh: number;
  pending_review_items: number;
  runs_completed_24h: number;
  runs_failed_24h: number;
  crawl_failures_24h: number;
  provider_failures_24h: number;
  businesses_fresh_percent: number;
  offers_fresh_percent: number;
  freshness_note: string;
}

export interface AdminDeal {
  id: string;
  title: string;
  description: string | null;
  deal_type: string;
  publication_state: string;
  freshness_status: string;
  sighting_state: string;
  extraction_method: string | null;
  source_confidence: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
  last_verified_at: string | null;
  next_refresh_at: string | null;
  consecutive_misses: number;
  raw_source_text: string | null;
  venue_id: string | null;
  venue_name: string | null;
  source_id: string | null;
  snapshot_id: string | null;
}

export interface AdminVenue {
  id: string;
  name: string;
  slug: string;
  status: string;
  website_url: string | null;
  phone: string | null;
  city: string | null;
  address: string | null;
  freshness_status: string;
  last_verified_at: string | null;
  last_seen_at: string | null;
  next_refresh_at: string | null;
  failure_count: number;
  provider_links: {
    provider: string;
    provider_business_id: string;
    provider_url: string | null;
    last_seen_at: string | null;
  }[];
  location_id: string | null;
  timezone: string | null;
  offers: AdminDeal[];
}

export interface AdminRun {
  id: string;
  provider: string;
  job_type: string;
  status: string;
  requested_by: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  target_url: string | null;
  venue_id: string | null;
  records_discovered: number;
  records_created: number;
  records_updated: number;
  records_skipped: number;
  pages_discovered: number;
  pages_fetched: number;
  pages_skipped: number;
  robots_blocked: number;
  offers_discovered: number;
  offers_created: number;
  offers_updated: number;
  retry_count: number;
  error_category: string | null;
  error_details: string | null;
  errors: unknown[];
  extra_metadata: Record<string, unknown>;
  cancel_requested: boolean;
}

export interface AdminProvider {
  name: string;
  configured: boolean;
  enabled: boolean;
  key_configured: boolean;
  last_status: string | null;
  last_finished_at: string | null;
  calls_today: number;
  errors_today: number;
  rate_limits_today: number;
  records_imported_today: number;
  note: string | null;
}

export interface AdminReview {
  id: string;
  subject_type: string;
  subject_id: string | null;
  reason: string;
  status: string;
  title: string;
  explanation: string;
  suggested_action: string | null;
  evidence: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

export interface AdminErrorGroup {
  category: string;
  provider: string | null;
  count: number;
  first_at: string;
  latest_at: string;
  example: string | null;
}

export interface AdminSystem {
  api: string;
  postgres: string;
  redis: string;
  worker: string;
  crawler: string;
  google: string;
  yelp: string;
  tripadvisor?: string;
  opentable: string;
  maps?: string;
  geocoding?: string;
  geocodes_today?: number;
  locations_waiting_geocode?: number;
}

export interface AdminMapQuality {
  total_locations: number;
  published_locations: number;
  map_eligible: number;
  map_ineligible: number;
  needs_review: number;
  invalid: number;
  missing_geocode_source: number;
  geocodes_today: number;
  geocoding_configured: boolean;
  items: {
    id: string;
    venue_id: string | null;
    venue_name: string | null;
    address: string;
    city: string;
    latitude: string;
    longitude: string;
    location_confidence: string;
    geocode_source: string | null;
    geocode_accuracy: string | null;
  }[];
}

export interface AdminFreshness {
  buckets: Record<string, number>;
  items: AdminDeal[];
  page: number;
  page_size: number;
  total: number;
}

export interface CrawlDomain {
  host: string;
  last_attempt_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_http_status: number | null;
  success_count: number;
  failure_count: number;
  consecutive_failures: number;
  robots_status: string | null;
  avg_response_ms: number | null;
  next_permitted_at: string | null;
  last_error: string | null;
}

export interface AdminSearch {
  venues: AdminVenue[];
  deals: AdminDeal[];
  runs: AdminRun[];
}

export interface AdminAudit {
  id: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
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
  q?: string;
  cuisine?: string;
  price_level?: string;
  drink?: string;
  reservations?: boolean;
  feature?: string;
  when?: string;
  day?: string;
  min_rating?: string;
  rating_source?: string;
  sort?: string;
  vertical?: Vertical;
  page?: number;
  page_size?: number;
}
