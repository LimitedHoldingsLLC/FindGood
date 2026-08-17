# Contributing to FindGood

Read [ARCHITECTURE.md](ARCHITECTURE.md) first. If a change would surprise a future engineer about *where* behavior lives, stop and put it in the owning module.

## Branches

- `main` is always deployable.
- Feature branches: `feat/<short-name>`
- Fixes: `fix/<short-name>`
- Schema-only: `db/<short-name>`

Keep pull requests small enough to review in one sitting.

## Modules

- HTTP route handlers validate input and call an application service. They do not contain business rules.
- Domain services have no FastAPI, Redis, or HTTP client imports.
- Persistence goes through repositories. Do not query the session from a route.
- Ingestion adapters (fetchers, parsers, extractors) are isolated. Do not import them from consumer API routes.
- New product features get a domain module or an application service. Do not grow `main.py`.

If you cannot name the owning module, you do not understand the change yet.

## Naming

- Python: modules `snake_case`, classes `PascalCase`, enums `SCREAMING_SNAKE` values in lowercase strings (`happy_hour`).
- TypeScript: files `kebab-case` or feature-folder `PascalCase` components.
- Database tables: plural `snake_case` (`venue_locations`, `deal_schedules`).
- API fields: `snake_case` JSON. Do not camelCase the public API.

## Migrations

- Every schema change needs an Alembic revision.
- Never edit a revision that may already have run in any shared environment. Add a new revision.
- Indexes belong in the migration, not as an afterthought.
- Soft-status fields (`status`, `publication_state`) are preferred over hard deletes when history or provenance matters.

## Tests

Update tests in the same change as the behavior.

Required coverage when you touch:

| Area | Test |
| --- | --- |
| Schedules / timezones | `tests/unit/test_schedule_engine.py` |
| Prices / money | `tests/unit/test_money.py` |
| Normalization | `tests/unit/test_normalizer.py` |
| Publishing / provenance | `tests/integration/test_publishing.py` |
| Ingestion / crawler safety | `tests/unit/test_fetcher_safety.py` |
| Admin auth | `tests/integration/test_admin_auth.py` |
| Public consumer API | `tests/contract/test_consumer_api.py` |
| Vertical defaulting | `tests/unit/test_verticals.py` |

Do not add tests that only assert mocks were called.

## Environment variables

- Add new variables to `.env.example` and `app/core/config.py` together.
- Never default production secrets.
- Frontend public variables must be prefixed `NEXT_PUBLIC_` and must never include secrets.

## Logging

- Use structured log events (`logger.info("source_fetch_failed", source_id=..., crawl_run_id=...)`).
- Include `request_id` / `crawl_run_id` when available.
- Never log secrets, admin passwords, session tokens, or full raw snapshots at info level.
- Never swallow exceptions.

## API changes

- Public routes live under `/api/v1/`.
- Additive changes are preferred.
- Do not silently rename or remove response fields.
- Update Pydantic response schemas and frontend `lib/api` types in the same PR.
- Regenerate or hand-update the consumer client. Do not drift a parallel hardcoded model.

## Ingestion

- Never publish crawler output implicitly.
- SourceSnapshots are immutable. Do not add an update path.
- New fetchers/parsers/extractors implement the existing protocols.
- SSRF protections apply to every network fetcher.

## Commit messages

Write the *why* in one or two sentences.

```
Add immutable source snapshots so published deals stay auditable.
```
