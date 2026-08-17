# FindGood data model

One canonical Postgres database. There is no `food_database` or `deals_database`.

Money is `Numeric` / `Decimal`. Coordinates are real columns. Schema changes go through Alembic. Do not edit applied revisions.

## Vocabulary

`Venue` is the business. `VenueLocation` is a place. `Deal` is an offer. Those names are what the database and `/api/v1` use today. This document uses both so later verticals do not invent parallel tables.

## Shipped entities

```text
Venue                              # business identity
  └── VenueLocation                # address, city, neighborhood, lat/lng, timezone
        └── Deal                   # offer (type, offering_kind, vertical, publication_state)
              ├── DealSchedule     # ISO weekdays, start/end, valid_from/until
              ├── DealItem         # priced line (normal_price, deal_price)
              └── DealPublication  # provenance link
                    ├── ExtractionCandidate
                    └── SourceSnapshot (immutable)
                          └── Source

Verification                       # subject_type + subject_id (not deal-only)
CrawlRun                           # one fetch/parse/extract attempt
IngestionRun                       # operator-facing job (search, crawl, refresh)
VenueProviderLink                  # google_places / yelp / opentable / website id
ReviewItem                         # human review queue beyond extraction candidates
AdminAuditLog                      # manual admin actions
CrawlDomain                        # per-host crawler health
ProviderUsageDaily                 # API call counters
ErrorEvent                         # grouped operational errors
```

Provenance for a consumer-visible offer:

**Deal → DealPublication → ExtractionCandidate → SourceSnapshot → Source → URL**

Manually created admin deals still get a publication row (and usually a `manual` source) so “why do we believe this?” always has an answer.

### Venue (business)

| Column | Role |
| --- | --- |
| `name`, `slug` | Identity. Slug is unique. |
| `website_url`, `phone` | Business-level contact. Location-specific phone/site is not shipped. |
| `primary_category` | Free string. Seed uses `gastropub`, `mexican`, `seafood`, `cafe`, `bar`. Default in admin create is `restaurant`. |
| `cuisines` | Controlled taxonomy array (`mexican`, `seafood`, …). Consumer `?cuisine=` matches this or `primary_category`. |
| `price_level` | 1–4 venue price band (`$`–`$$$$`). Not deal-item prices. |
| `drink_kinds` | Controlled array: `cocktails`, `beer`, `wine`, `natural_wine`, `sake`, `nonalcoholic`. |
| `accepts_reservations` | Whether the business takes reservations. Booking URLs stay off this table. |
| `features` | Controlled array: `patio`, `rooftop`, `outdoor`, `late_night`, `good_for_groups`, `walk_in`. |
| `vertical` | Controlled taxonomy. Default `food`. Consumer list endpoints default to `food` when the query param is omitted. |
| `status` | `draft` / `published` / `archived` / `disabled` |

### VenueLocation

Geography and schedule timezone live here, not on the venue and not in JSON.

A venue may have many locations. Today every deal attaches to **exactly one** location (`deals.venue_location_id` is required).

### Deal (offer)

| Column | Role |
| --- | --- |
| `venue_location_id` | Required. Offer scope is location-only. |
| `deal_type` | Food-centric enum: `happy_hour`, `food_special`, `drink_special`, `prix_fixe`, `oyster`, `taco_night`, `brunch`, `lunch`, `late_night`, `limited_time`, `other` |
| `offering_kind` | `food` / `drink` / `both` |
| `vertical` | Same taxonomy as venues. Default `food`. Inherited from the venue on ingest publish when the candidate omits it. |
| `status` | Record lifecycle |
| `publication_state` | `unpublished` / `published` / `withdrawn` — consumer lists only published + published venue/location |
| `source_confidence` | `Numeric(4,3)` |

Prices are **not** required on the deal row. They live on `DealItem` so an offer can be “see menu.”

### DealSchedule

Structured recurrence. The schedule engine evaluates windows in the **location timezone**.

- `days_of_week`: ISO-8601 Monday=1 … Sunday=7
- Overnight windows: `end_time <= start_time`
- `ends_at_close` with no `end_time` means “until close”

### Source / snapshot / candidate

| Entity | Role |
| --- | --- |
| `Source` | URL + type + trust + crawl switch. Optional `venue_id`. |
| `SourceSnapshot` | Immutable raw evidence. No `updated_at`. Do not overwrite. |
| `ExtractionCandidate` | Unpublished structured output. `review_status` starts `pending`. |
| `DealPublication` | Links a live deal to candidate/snapshot/source. Unique on `candidate_id`. |
| `CrawlRun` | Job outcome, error category, retry count. |

`SourceType` values today include restaurant-specific names (`restaurant_website`, `restaurant_html_menu`, …). Treat those as food-vertical source kinds, not as a reason to create a second source table.

### Verification

Append-only. `subject_type` + `subject_id` so freshness can apply to deals now and to businesses/locations later without a new table.

Freshness labels are derived in `domain/verification/freshness.py` (today / 1 day / N days; fresh if ≤ 7 days). Scores must stay explainable.

## Indexes that exist

- Venue slug, status, `primary_category`, `vertical`, `price_level`, `accepts_reservations`
- Location venue, city, neighborhood, status, `(latitude, longitude)`
- Deal location, `(status, publication_state)`, `deal_type`, `offering_kind`, `vertical`, `(vertical, status, publication_state)`
- Source venue, `(is_active, crawl_enabled)`, unique `canonical_identity`
- Snapshot source, content hash
- Candidate snapshot, review, validation
- Verification `(subject_type, subject_id)`

## Planned additive columns (not shipped)

| Change | Purpose |
| --- | --- |
| `deals.scope` + nullable `deals.venue_id` | Business-wide or multi-location offers |
| `transaction_destinations` | Order / reserve / book URLs; no provider columns on `venues` |
| `clicks` / `conversions` | Attribution |
| External IDs on venues | Shipped as `venue_provider_links` |

Do **not** add required `normal_price` / `start_time` on `deals`. Items and schedules already hold those.

## Identity resolution

`SimpleDuplicateMatcher` plus `classify_match` run on provider imports. Provider IDs live on `venue_provider_links`. Auto-merge requires a strong second signal (phone, website, or nearby same name). Name+city alone goes to the review queue. Fuzzy name matching stays out of the matcher.

## What must not happen

- Separate databases per vertical
- Copying the same restaurant into a “deals” catalog
- Overwriting `source_snapshots`
- Publishing a consumer deal with no publication row
- Float money columns
