# FindGood Architecture

FindGood is a **modular monolith** with independently runnable workers. One deployable API process, one worker process, one Postgres database, one Redis/Valkey-compatible queue. The Next.js app is a separate deployable.

This is intentional. We optimize for a fast MVP *and* for isolated changes. We do not split microservices until a module has an independent scale, failure, or team boundary that the monolith cannot absorb.

**Platform intent:** one FindGood core, many consumer applications. FindGood.food (`apps/web`) is the first interface, not the database. Tables named `venues` and `deals` are the business and offer graph. Do not copy that graph per vertical.

Platform docs (current vs target, data model, ingestion, deploy, adding a vertical) live in [`docs/`](docs/). This file remains the implementation contract for code changes.

## Vocabulary

| Platform | Code / API today | Do not do |
| --- | --- | --- |
| Business | `Venue`, `/api/v1/venues` | Rename tables to launch a vertical |
| Location | `VenueLocation` | Store lat/lng only in JSON |
| Offer | `Deal`, `/api/v1/deals` | Create `HappyHourRestaurant` |
| Evidence | Source → Snapshot → Candidate → Publication | Auto-publish crawler output |

Public JSON field names are locked by `services/backend/tests/contract/`. Additive fields are allowed. Renames and removals need an explicit instruction and a food-app update in the same change.

## High-level diagram

```
                    ┌──────────────────┐
   browsers  ──────►│  apps/web        │  Next.js / Vercel
                    │  consumer + admin│
                    └────────┬─────────┘
                             │ HTTP /api/v1
                    ┌────────▼─────────┐
   cron ──enqueue──►│  services/backend│  FastAPI / Render
                    │  API process     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        PostgreSQL      Job queue       Domain +
        (Render)        (Redis/KV)      ingestion
                             │
                    ┌────────▼─────────┐
                    │  worker process  │  same codebase
                    └──────────────────┘
```

Cron jobs **only enqueue work**. They do not fetch, parse, or publish.

## Component responsibilities

| Component | Owns | Must not own |
| --- | --- | --- |
| `app/api` | Authn/z at the edge, request validation, response schemas, request IDs | Deal status math, publishing, SQL |
| `app/domain` | Schedules, scoring, verification freshness, duplicate matching interfaces | FastAPI, HTTP, Redis |
| `app/services` | Use-cases: list deals, publish candidate, refresh source | Raw SQL, HTML parsing |
| `app/db` | Models, repositories, Alembic | HTTP routes, crawler fetchers |
| `app/ingestion` | Fetch/parse/extract/normalize/validate/publish pipeline | Consumer page rendering |
| `app/workers` | Queue protocol, job names, retry/ack | Domain rules |
| `app/adapters` | Maps, geocoding, analytics vendors | Business decisions |
| `app/core` | Config, logging, security, feature flags, errors | Feature logic |
| `apps/web` | Discovery UX, admin chrome, SEO metadata | Canonical deal status calculation |

## Allowed dependency directions

```
api  →  services  →  domain
                ↘  db/repositories  →  db/models
                ↘  ingestion (admin/worker use-cases only)
                ↘  adapters

workers  →  services  →  (same as above)

domain  →  (stdlib, pydantic).  NOTHING ELSE.

ingestion/fetchers  must not import parsers, extractors, or publishers.
ingestion/publishers  may use services + repositories.
apps/web  talks to the API contract only.
```

Circular imports are a design smell. If A and B need each other, extract a third module.

The domain layer does not know FastAPI exists.

## Data lifecycle

```
Venue
  └── VenueLocation (1+; geography lives here, not in JSON)
        └── Deal (conceptual promotion)
              ├── DealSchedule (structured recurrence)
              ├── DealItem (priced offers; Decimal money)
              ├── Verification
              └── DealPublication
                    ├── ExtractionCandidate
                    └── SourceSnapshot (immutable)
                          └── Source
```

A consumer-visible deal must be traceable backward:

**Deal → DealPublication → ExtractionCandidate → SourceSnapshot → Source → original URL**

Manually created admin deals still get a `manual` source and a publication row so the question *why do we believe this?* always has an answer.

### Why SourceSnapshots are immutable

Raw evidence is the company's audit trail. If a parser improves next week, we re-parse the snapshot; we do not lose what the restaurant's site said on Tuesday. Overwriting snapshots would make incorrect publications undiagnosable.

## Ingestion lifecycle

```
cron / admin refresh
  → enqueue_source_refresh(source_id)
  → worker
      1. open CrawlRun
      2. Fetcher.get(source)          # bytes + metadata only
      3. persist SourceSnapshot       # immutable
      4. Parser.parse(snapshot)
      5. Extractor.extract(...)       # candidates, not live deals
      6. Normalizer.normalize(...)
      7. Validator.validate(...)      # reject / quarantine
      8. persist ExtractionCandidate  # review_status=pending
      9. close CrawlRun
  → human or trusted publisher
      10. Publisher.publish(candidate)  # explicit
```

Crawler output never becomes consumer-facing without step 10.

### Adding a crawler adapter

1. Implement `Fetcher` / `Parser` / `Extractor` protocols in `app/ingestion/...`.
2. Wire them in one place (`IngestionPipeline` today; a registry when a second real adapter exists).
3. Do not put extraction logic in a fetcher.
4. An `LLMExtractor` later implements the same `Extractor` protocol. Do not special-case the pipeline.
5. Every network fetcher must go through `ingestion/safety.py` (scheme, DNS, private IP, size, timeout, robots).
6. Add a unit test with a fixture. Do not crawl a live site to prove the adapter works.

## Deal status engine

`domain/schedules/engine.py` answers, in the **venue location timezone**:

- `active_now`
- `starts_soon`
- `active_later_today`
- `ended_today`
- `next_occurrence`
- `currently_unavailable`

Never use the server timezone. Never treat schedule text as a blob.

## API boundaries

- Public: `/api/v1/...`
- Health: `/health`, `/ready` (unversioned, for orchestrators)
- Admin: `/api/v1/admin/...` (username/password session, or `X-Admin-Key`)
- Responses are Pydantic schemas. ORM objects never leave the repository layer.
- Collection endpoints are paginated.
- Source snapshots are not returned on consumer deal payloads.

The frontend client in `apps/web/src/lib/api` mirrors the OpenAPI contract and is structured so a generator can replace it later.

## Feature flags

`app/core/feature_flags.py` and `apps/web/src/lib/flags.ts` read environment booleans. No third-party flag service yet.

Current flags: `deal_score`, `maps`, `accounts`, `community_verification`, `flash_deals`, `restaurant_portal`, `ai_extraction`.

## Maps, location, analytics

- Coordinates are real columns on `venue_locations`.
- Browser geolocation is optional. Neighborhood / city selection must work without it.
- `adapters/maps.py` and `apps/web/src/lib/maps.ts` are the only vendor-shaped seams.
- A list-first MVP works with maps disabled.
- Analytics events go through one adapter. Components emit `deal_impression`, never `gtag(...)`.

## Auth

`core/security.py` defines an `AuthN` boundary. Today it only protects internal admin: operators sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`, receive a signed session token, and call `/api/v1/admin/*` with `Authorization: Bearer`. Password guesses are locked after 5 failures per client in 15 minutes, or 25 failures globally. `ADMIN_API_KEY` signs those tokens and remains valid as `X-Admin-Key` for scripts. Consumer and restaurant identity can implement the same protocols later. Do not invent a custom identity platform now.

## Deployment details vs application code

Render and Vercel are **not imported** by application modules. Processes are selected by command:

- API: `uvicorn app.main:app`
- Worker: `python -m app.workers.runner`
- Cron: `python -m app.workers.enqueue_stale`

## HOW TO ADD A FEATURE WITHOUT BREAKING THE SYSTEM

Follow this procedure every time. It is written for human engineers and AI coding agents.

### 1. Inspect before you write

- Read this file and the owning module's `__init__.py` / README-equivalent docstring.
- Search for an existing service, repository method, or component that already does the job.
- If you are about to add a dependency, stop and justify it against the current stack.

### 2. Name the owner

Pick one:

- Consumer read path → `services/deal_service.py` or `venue_service.py`
- Admin write path → `services/admin_service.py`
- Time / recurrence → `domain/schedules`
- Provenance / publish → `ingestion/publishers` + `services/ingestion_service.py`
- New catalog concept → new package under `app/domain/<name>/`

If the change touches more than two owners, split the work.

### 3. Keep transport thin

```
request → API schema validation → application service → repository → response schema
```

No SQL in routes. No deal-status math in React components. Components may *display* `availability.status` from the API.

### 4. Preserve provenance

If the feature creates or changes a consumer-visible deal:

- You must be able to walk Deal → publication → snapshot → source → URL.
- Do not add a write path that inserts a published deal with no publication row.
- Do not update `source_snapshots` in place.

### 5. Never auto-publish crawler output

Extraction creates candidates. Publishing is an explicit service call.

### 6. Schema changes

- Add an Alembic revision.
- Add indexes for the query you are introducing.
- Prefer columns over JSON unless the shape is genuinely variable metadata.

### 7. API compatibility

- Additive fields are fine.
- Renames and removals require an explicit instruction and a frontend update in the same change.
- Update OpenAPI by changing Pydantic models; do not hand-edit a stale spec as the source of truth.

### 8. Tests and proof

- Change tests with behavior.
- Run the relevant pytest module and, if UI-facing, the frontend unit test or typecheck.
- Do not claim completion because files were generated.

### 9. Report the change

When done, list the files touched and the reason for each. If you added a folder, state its responsibility in the PR or chat report.

### 10. Feature removal

New capabilities should be deletable by removing one domain package, its repository methods, its routes, and its frontend feature folder. If deleting a feature requires surgery across ten unrelated files, the boundary was wrong.

## What this foundation deliberately does not include

Native mobile, ML recommendations, restaurant billing, reservations, POS, nationwide crawling, Kubernetes, event sourcing, GraphQL. Seams exist; implementations do not.

Empty `apps/deals` / `apps/merchant` shells, Turborepo, and Venue→Business table renames are also out until a second product or an explicit migration phase needs them.

## Decision log

### Phase 1 — documentation and consumer API contract lock (2026-08-15)

```text
DECISION: Freeze FindGood.food’s public API in tests and write platform docs. No schema or folder moves.
OPTIONS: Rename Venue/Deal now / extract packages now / docs+contract only
RECOMMENDATION: Docs + contract tests only
WHY: The working food app is the asset. Venue/Deal already are Business/Offer. Renames and empty apps would break velocity without a second product.
TRADEOFF: Public routes still say /venues and /deals.
REVERSIBILITY: High. Docs and tests can be extended when vertical columns land.
```

### Admin username/password sessions (2026-08-16)

```text
DECISION: Admin UI signs in with env username/password and a signed session token. No user table.
OPTIONS: Keep paste-the-API-key / env credentials + HMAC token / full identity platform
RECOMMENDATION: Env credentials + HMAC token in core/security.py
WHY: Operators need a normal login form. Consumer accounts are still out of scope. Reuse the existing AuthN boundary.
TRADEOFF: One operator identity from env, not per-person accounts. X-Admin-Key remains for scripts.
REVERSIBILITY: High. A later user table can implement the same AuthN protocol.
```

### Ingestion engine, freshness, and admin control plane (2026-08-16)

```text
DECISION: Extend Venue/Deal/Source/CrawlRun. Add provider links, ingestion_runs, review, audit, crawl domain health, and a policy module for freshness. Do not rename tables to Business/Offer.
OPTIONS: Parallel businesses/offers schema / generalize CrawlRun only / additive engine on existing graph
RECOMMENDATION: Additive engine on the existing Venue/Deal graph
WHY: Platform docs already say Venue is Business and Deal is Offer. A second graph would split the catalog.
TRADEOFF: Public routes still say /venues and /deals. Admin UI uses “business/offer” language.
REVERSIBILITY: High. New tables drop in 0003 downgrade. Additive columns on venues/deals are nullable or defaulted.
```

### FindGood.Food composite ratings (2026-08-17)

```text
DECISION: Official Google Places + Yelp Fusion scores become a Bayesian composite on Venue.rating. Consumer filter is ?min_rating=. Do not scrape review sites.
OPTIONS: Show each provider’s stars / scrape HTML reviews / composite from official APIs
RECOMMENDATION: Composite from official APIs
WHY: Provider terms restrict redistributing Google/Yelp stars as if they were ours. A weighted composite is FindGood.Food’s own score and stays explainable. HTML scraping would fight access controls.
TRADEOFF: No live Tripadvisor/OpenTable stars until those have authorized adapters. Thin 5.0s shrink toward 3.8.
REVERSIBILITY: High. 0005 downgrade drops the columns. New query param is additive.
```

### Consumer discovery filters (2026-08-17)

```text
DECISION: Compact popover buttons on the food home. Facets live on Venue; time-of-day uses DealSchedule in the location timezone. Search is ?q=.
OPTIONS: Keep every chip visible / sidebar / venue JSON blob / additive venue columns + schedule domain
RECOMMENDATION: Additive venue columns + schedule window matching
WHY: Neighborhoods already overflow the chip row. Cuisine, price, drinks, and reservations describe the business, not one offer. Schedule math already exists and must stay off UTC.
TRADEOFF: Reservation *availability* is not live inventory — only “takes reservations.” Booking links stay for transaction_destinations later.
REVERSIBILITY: High. 0004 downgrade drops the columns. New query params are additive.
```

### Phase 2 — additive vertical (2026-08-16)

```text
DECISION: Add venues.vertical and deals.vertical, default food. Consumer lists default to food when ?vertical= is omitted.
OPTIONS: Omit = all verticals / omit = food / require the query param
RECOMMENDATION: Omit = food; food app also sends vertical=food
WHY: FindGood.food must not start showing beauty rows when the first non-food business is inserted. Additive field; no table renames.
TRADEOFF: A future deals app cannot get “all verticals” by omitting the param until we add an explicit all/multi value.
REVERSIBILITY: High. Alembic downgrade drops the columns. Clients ignore unknown JSON fields.
```
