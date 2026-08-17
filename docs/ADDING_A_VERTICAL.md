# Adding a FindGood vertical

A vertical is a **query and presentation slice** of the same business / location / offer graph. It is not a new database, API, or ingestion platform.

FindGood.food is the first vertical (food and drink specials). This checklist is what “launch FindGood.beauty” should look like once Phase 2+ exists. **Items marked shipped are true today. Items marked later are not built.**

## Target sequence

1. **Taxonomy** — `vertical` column on venues and deals. Values: `food`, `beauty`, `fitness`, `entertainment`, `activities`, `retail`, `services`, `health`, `travel`, `other`. Default `food`. Consumer lists omit or pass `?vertical=food`.
2. **Ingestion** — add adapters only if this vertical has a new source shape. Reuse Source / Snapshot / Candidate / Publish. Do not copy the pipeline.
3. **Consumer app** — later: `apps/<vertical>` with its own UX, domain, and SEO. Today: FindGood.food (`apps/web`) sends `vertical=food`.
4. **Query** — `GET /api/v1/deals?vertical=food` (omitted also means food). A future deals app can pass another value or, later, an `all` mode.
5. **Domain** — later: Vercel project + `NEXT_PUBLIC_*` for that app. Canonical host must not duplicate findgood.food URLs blindly.
6. **Analytics** — emit the shared event names with `app` and `vertical` properties. Adapter already exists; persistence does not.
7. **Deploy** — independent Vercel project; same Render API and database.

If a step requires a new Postgres or a `/beauty/happy-hours` route that copies food deals, the boundary is wrong.

## What you may change per vertical

- Categories and offer-type values that apply to that vertical
- Ingestion fixtures/adapters for that vertical’s sources
- Frontend filters, copy, and SEO titles
- Which transaction destination types you surface (once destinations exist)

## What you must not change per vertical

- Canonical `venues` / `venue_locations` / `deals` rows
- Schedule engine timezone rules
- Money as `Decimal`
- Snapshot immutability and explicit publish
- Admin authorization
- A second copy of ranking or freshness logic in the app

## Food-specific values (do not treat as platform identity)

These are valid **food** enumerations. They are not the definition of FindGood.

- `DealType`: `happy_hour`, `taco_night`, `oyster`, `brunch`, …
- `DealOfferingKind`: `food` / `drink` / `both`
- `SourceType`: `restaurant_website`, `restaurant_html_menu`, …
- Frontend chips: Food / Drinks / Happening now
- Acquisition host: `happyhour.food`

A beauty vertical should add its own offer types (for example `introductory_offer`) rather than overloading `happy_hour`.

## First vertical that is not food

1. Insert or ingest a non-food business in the **same** database with `vertical=beauty` (or the new value).
2. Confirm FindGood.food with no `vertical` param and with `vertical=food` still returns only food.
3. Confirm `?vertical=beauty` returns the new row.
4. Then consider `apps/deals` or `apps/beauty`.

## Contract

`services/backend/tests/contract/` locks the food consumer API. A vertical that needs a breaking change to `/deals` or `/venues` is not allowed to land without an explicit contract update and a food-app client update in the same change.
