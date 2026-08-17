# FindGood deployment

Render and Vercel are **not imported** by application code. Processes are selected by command.

## Topology (shipped)

```text
Vercel  apps/web                 → findgood.food
                                   /admin is the same project (robots-disallowed)

Render  findgood-api             uvicorn app.main:app
        findgood-worker          python -m app.workers.runner
        findgood-enqueue-stale   python -m app.workers.enqueue_stale   (hourly)
        findgood-postgres        Postgres 16, database name findgood
        findgood-kv              Redis-compatible queue
```

Blueprint: [`render.yaml`](../render.yaml). Frontend: Vercel project rooted at `apps/web`.

Local infrastructure is Docker Compose Postgres + Redis only. The API, worker, and Next.js app run on the host. See the root [`README.md`](../README.md).

## Future topology (do not build empty)

| App | Host | When |
| --- | --- | --- |
| `apps/food` | findgood.food | Rename/split of today’s `apps/web` consumer |
| `apps/deals` | findgood.deals | When the deals product exists |
| `apps/merchant` | merchant host | When claim/edit is real |
| `apps/admin` | protected host | When `/admin` outgrows one page |

Keep one API process and one worker until crawl CPU or failure isolation requires a split. Cron must remain enqueue-only.

Acquisition domain `happyhour.food` is an alias. Do not deploy a second copy of the site. Canonical URLs stay on findgood.food.

## Environment variables

Never commit `.env`. Templates: [`.env.example`](../.env.example), [`apps/web/.env.example`](../apps/web/.env.example).

| Variable | Scope | Secret? |
| --- | --- | --- |
| `DATABASE_URL` | platform / API / worker / cron | yes |
| `REDIS_URL` | platform / API / worker / cron | yes |
| `ADMIN_USERNAME` | platform / API | yes |
| `ADMIN_PASSWORD` | platform / API | yes |
| `ADMIN_API_KEY` | platform / API (session signing + `X-Admin-Key`) | yes |
| `ADMIN_SESSION_TTL_SECONDS` | platform / API; default 43200 | no |
| `ADMIN_LOGIN_MAX_FAILURES` | platform / API; default 5 | no |
| `ADMIN_LOGIN_WINDOW_SECONDS` | platform / API; default 900 | no |
| `ADMIN_LOGIN_LOCKOUT_SECONDS` | platform / API; default 900 | no |
| `ADMIN_LOGIN_GLOBAL_MAX_FAILURES` | platform / API; default 25 | no |
| `QUEUE_BACKEND` | `redis` or `memory` | no |
| `APP_ENV`, `LOG_LEVEL`, `LOG_FORMAT` | environment | no |
| `CORS_ALLOWED_ORIGINS` | API; comma-separated; no `*` in production | no |
| `API_BASE_URL`, `WEB_BASE_URL` | platform URLs | no |
| `CANONICAL_HOST`, `ACQUISITION_HOST` | SEO / aliases | no |
| `FEATURE_*` | platform flags | no |
| `CRAWLER_*` | ingestion | no |
| `GOOGLE_PLACES_API_KEY`, `YELP_API_KEY`, `OPENTABLE_API_KEY` | ingestion providers | yes |
| `GOOGLE_PLACES_MAX_CALLS_PER_RUN`, `YELP_MAX_CALLS_PER_RUN`, `CRAWLER_MAX_PAGES_PER_RUN` | cost caps | no |
| `BUSINESS_STALE_AFTER_DAYS`, `HAPPY_HOUR_STALE_AFTER_DAYS`, … | freshness windows | no |
| `RATE_LIMIT_ENABLED`, `RATE_LIMIT_PER_MINUTE` | API (in-process; one instance) | no |
| `NEXT_PUBLIC_API_BASE_URL` | food app | no (public) |
| `NEXT_PUBLIC_SITE_URL` | food app | no (public) |
| `NEXT_PUBLIC_CANONICAL_HOST` | food app | no (public) |

`NEXT_PUBLIC_*` is inlined into the browser bundle. Never put admin passwords, session secrets, or database URLs there.

The Settings defaults `ADMIN_PASSWORD=change-me-to-a-strong-admin-password` and `ADMIN_API_KEY=change-me-to-a-long-random-admin-key` are local footguns. Production must set a strong username, password, and signing key in the Render dashboard (`sync: false` in `render.yaml`). The browser never sees `ADMIN_PASSWORD` or `ADMIN_API_KEY`; it stores only the short-lived session token from `POST /api/v1/admin/session`.

## Health

| Path | Use |
| --- | --- |
| `GET /health` | Process is up |
| `GET /ready` | Postgres `SELECT 1` and Redis ping when `QUEUE_BACKEND=redis` |

Render API `healthCheckPath` is `/health`.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml):

- Backend: ruff format/check, mypy, `alembic upgrade head`, pytest (Postgres service, `QUEUE_BACKEND=memory`)
- Frontend: npm ci, lint, typecheck, vitest, `next build`

## Observability (shipped)

Structured logs (`structlog`), `X-Request-ID` / `request_id`, crawl_run_id and ingestion_run_id on ingestion logs. No paid error tracker yet. Prefer fixing log gaps over adding a vendor.

## Cost and optional workers

The existing hourly cron stays enqueue-only. It now also enqueues freshness detect/expire. The worker must be running for queued crawls and provider searches.

Operator runbook: [`docs/OPERATOR.md`](./OPERATOR.md).

Current Render plans in `render.yaml` are free API/worker/Postgres/KV plus a starter cron. Do not add paid search, a second database, or Kubernetes. Upgrade a specific process when that process is the bottleneck. Do not create extra paid Render services automatically.
