# FindGood platform architecture

This document is the **platform** view: one core, many applications.

Implementation ownership, dependency rules, and the “how to add a feature” checklist live in the repository-root [`ARCHITECTURE.md`](../ARCHITECTURE.md). Read that file before changing code. This file records the product-platform intent and what has actually shipped.

## Principle

> One FindGood platform. One canonical data engine. Multiple independent applications.

FindGood.food is the first consumer interface. It is not the platform.

A restaurant happy hour stored once in FindGood Core must be able to appear on FindGood.food and, later, FindGood.deals without being copied.

## Current vs target

| | Shipped today | Target (not built yet) |
| --- | --- | --- |
| Consumer app | `apps/web` on findgood.food (admin at `/admin`) | `apps/food`, `apps/deals`, `apps/merchant`, `apps/admin` |
| API | One FastAPI process: `/api/v1/venues`, `/api/v1/deals` | Same process; additive aliases such as `/offers` only when needed |
| Workers | Same codebase, separate Render process | Same until isolation is required |
| Database | One Postgres | Still one Postgres |
| Shared JS packages | None | `packages/types` when a second app exists |
| Vertical filter | None (everything is food in practice) | `vertical=FOOD` vs all verticals |

Do not create empty app shells or Turborepo until a second product is real.

## Vocabulary

Tables and public routes keep today’s names. Docs use platform names.

| Platform concept | Shipped name | Notes |
| --- | --- | --- |
| Business | `Venue` / `/venues` | Canonical identity. Not a restaurant-only type. |
| Location | `VenueLocation` | Geography and timezone live here. |
| Offer | `Deal` / `/deals` | Generic promotion with schedules and priced items. |
| Offer item | `DealItem` | Decimal money. Floats are rejected. |
| Source / evidence | `Source`, `SourceSnapshot`, `ExtractionCandidate`, `DealPublication` | Why we believe an offer exists. |
| Verification | `Verification` | Polymorphic (`subject_type` + `subject_id`). |

Renaming tables or routes is **not** Phase 1 and is not required to launch another vertical.

## What each application may own

A consumer application owns UX, routes, branding, SEO presentation, and vertical-specific filters.

It must not own canonical copies of businesses, locations, offers, verification, ingestion, ranking, or transaction routing.

Today that means: `apps/web` talks to `/api/v1` only. Availability, prices, and freshness are computed in the backend and displayed, not recalculated, in React.

## Shared core (already in `services/backend`)

- Business identity and locations
- Offer + schedule + item engine
- Source / snapshot / candidate / publish pipeline
- Timezone-aware availability
- Verification freshness
- Transparent deal scoring
- Exact-match duplicate matcher (not yet wired into writes)
- Geo bounding-box filter + haversine distance
- Admin username/password session (`core/security.py`); `X-Admin-Key` for machine callers
- Analytics and maps adapter seams

## Deliberately not built

Users, saved items, transaction destinations, click/conversion logs, merchant claims, `/search`, `/nearby` as dedicated routes, PostGIS, a deals app, a merchant app, a separate admin deploy.

## Contract lock

FindGood.food depends on the current public JSON shapes.

Backend contract tests in `services/backend/tests/contract/` require today’s fields and list filters to keep working. **Additive fields are allowed.** Renames and removals must update those tests in the same change as the frontend client.

## Related documents

- [DATA_MODEL.md](./DATA_MODEL.md) — tables and planned additive columns
- [INGESTION.md](./INGESTION.md) — collect → publish lifecycle
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Vercel, Render, environment variables
- [ADDING_A_VERTICAL.md](./ADDING_A_VERTICAL.md) — how a new vertical should land
