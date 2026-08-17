# Adding a FindGood vertical

A vertical is a **query and presentation slice** of the same business / location / offer graph. It is not a new database, API, or ingestion platform.

FindGood.food is the first vertical (food and drink specials). This checklist is what “launch FindGood.beauty” should look like once Phase 2+ exists. **Items marked shipped are true today. Items marked later are not built.**

## Target sequence

1. **Taxonomy** — add or reuse a `vertical` value (`FOOD`, `BEAUTY`, …) and categories. Later: additive columns defaulting existing rows to `food`. Today: `primary_category` is a free string; there is no vertical filter.
2. **Ingestion** — add adapters only if this vertical has a new source shape. Reuse Source / Snapshot / Candidate / Publish. Do not copy the pipeline.
3. **Consumer app** — later: `apps/<vertical>` with its own UX, domain, and SEO. Today: do not create an empty app. Filter in `apps/web` or wait until the product is real.
4. **Query** — later: `GET /api/v1/deals?vertical=BEAUTY` (or `/offers`). Today: `GET /api/v1/deals` with `city`, `neighborhood`, `food_or_drink`, `deal_type`, `active_now`.
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

Do this, in order, when the product is real:

1. Ship Phase 2: additive `vertical` on venues and deals, default `food`, optional `?vertical=` on existing list endpoints.
2. Seed or ingest one non-food business in the **same** database.
3. Confirm FindGood.food with no `vertical` param (or `vertical=food`) still returns only food.
4. Then consider `apps/deals` or `apps/beauty`.

Until step 1 exists, do not launch a second domain that reads a forked catalog.

## Contract

`services/backend/tests/contract/` locks the food consumer API. A vertical that needs a breaking change to `/deals` or `/venues` is not allowed to land without an explicit contract update and a food-app client update in the same change.
