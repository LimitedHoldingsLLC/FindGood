# FindGood data model

One canonical Postgres database. There is no `food_database` or `deals_database`.

Money is `Numeric` / `Decimal`. Coordinates are real columns. Schema changes go through Alembic. Do not edit applied revisions.

## Vocabulary

`Venue` is the business. `VenueLocation` is a place. `Deal` is an offer. Those names are what the database and `/api/v1` use today. This document uses both so later verticals do not invent parallel tables.

## Shipped entities

```text
Venue                              # business identity
  └── VenueLocation                # address, city, neighborhood, lat/lng, timezone
        └── Deal                   # offer (type, offering_kind, publication_state)
              ├── DealSchedule     # ISO weekdays, start/end, valid_from/until
              ├── DealItem         # priced line (normal_price, deal_price)
              └── DealPublication  # provenance link
                    ├── ExtractionCandidate
                    └── SourceSnapshot (immutable)
                          └── Source

Verification                       # subject_type + subject_id (not deal-only)
CrawlRun                           # one fetch/parse/extract attempt
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
| `status` | `draft` / `published` / `archived` / `disabled` |

There is **no** `vertical` column yet. Every current row is food in practice.

### VenueLocation

Geography and schedule timezone live here, not on the venue and not in JSON.

A venue may have many locations. Today every deal attaches to **exactly one** location (`deals.venue_location_id` is required).

### Deal (offer)

| Column | Role |
| --- | --- |
| `venue_location_id` | Required. Offer scope is location-only. |
| `deal_type` | Food-centric enum: `happy_hour`, `food_special`, `drink_special`, `prix_fixe`, `oyster`, `taco_night`, `brunch`, `lunch`, `late_night`, `limited_time`, `other` |
| `offering_kind` | `food` / `drink` / `both` |
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

- Venue slug, status, `primary_category`
- Location venue, city, neighborhood, status, `(latitude, longitude)`
- Deal location, `(status, publication_state)`, `deal_type`, `offering_kind`
- Source venue, `(is_active, crawl_enabled)`, unique `canonical_identity`
- Snapshot source, content hash
- Candidate snapshot, review, validation
- Verification `(subject_type, subject_id)`

## Planned additive columns (not shipped)

Do not implement these in Phase 1. When they land, they must be nullable or defaulted so FindGood.food keeps working.

| Change | Purpose |
| --- | --- |
| `venues.vertical`, `deals.vertical` default `food` | Let food query `FOOD` and deals query many verticals |
| `deals.scope` + nullable `deals.venue_id` | Business-wide or multi-location offers |
| `transaction_destinations` | Order / reserve / book URLs; no provider columns on `venues` |
| `clicks` / `conversions` | Attribution |
| External IDs on venues | Later identity resolution |

Do **not** add required `normal_price` / `start_time` on `deals`. Items and schedules already hold those.

## Identity resolution

`SimpleDuplicateMatcher` compares normalized name+city, phone digits, and website host. Exact signals only. It is not applied on ingest writes yet. Do not add a probabilistic matcher until duplicates are a real operational problem.

## What must not happen

- Separate databases per vertical
- Copying the same restaurant into a “deals” catalog
- Overwriting `source_snapshots`
- Publishing a consumer deal with no publication row
- Float money columns
