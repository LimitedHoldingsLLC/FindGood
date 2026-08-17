# FindGood

**Find good food and drink deals happening near you.**

FindGood helps consumers answer: *Where can I get something genuinely good for an unusually good price near me right now?*

The first vertical is restaurant food and drink specials — happy hours, taco nights, oyster specials, prix-fixe menus, brunch deals, and similar offers. The architecture does not assume the product will stay limited to restaurants.

Primary domain: [findgood.food](https://findgood.food)
Acquisition domain: [happyhour.food](https://happyhour.food) (do not duplicate the site; keep canonical URLs on findgood.food)

This repository is a **modular monolith**: one FastAPI backend, independently runnable workers, and a Next.js consumer app.

## Repository layout

```
apps/web/                 Next.js consumer + admin UI (Vercel)
services/backend/         FastAPI API, domain, ingestion, workers (Render)
docs/                     Platform architecture, data model, ingestion, deploy
scripts/                  Local developer helpers
.cursor/rules/            Instructions for AI coding agents
```

| Path | Responsibility |
| --- | --- |
| `apps/web/src/app` | Routes, layouts, SEO metadata |
| `apps/web/src/components` | Reusable presentational UI |
| `apps/web/src/features` | Feature-specific UI and hooks |
| `apps/web/src/lib` | API client, flags, analytics, maps adapters |
| `services/backend/app/api` | HTTP transport only |
| `services/backend/app/domain` | Pure business logic |
| `services/backend/app/db` | SQLAlchemy models, repositories, migrations |
| `services/backend/app/services` | Application services (use-cases) |
| `services/backend/app/ingestion` | Fetch → parse → extract → normalize → validate → publish |
| `services/backend/app/workers` | Queue abstraction and job runners |
| `services/backend/app/adapters` | External-system boundaries (maps, analytics) |

See [ARCHITECTURE.md](ARCHITECTURE.md) before changing structure. Platform intent and vertical rules: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Local setup

Prerequisites: Python 3.12+, Node 22+, and **Docker Desktop** (Postgres + Redis only). The API will not start without Postgres. Install Docker Desktop, then:

```bash
docker compose up -d
```

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
docker compose up -d
```

### Backend

```bash
cd services/backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000
OpenAPI: http://localhost:8000/docs

### Worker

In a second terminal, same venv:

```bash
cd services/backend
python -m app.workers.runner
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000
Admin: http://localhost:3000/admin (sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from `.env`)

### One-command local stack (optional)

From the repo root, after venvs/deps exist:

```bash
# Windows
powershell -File scripts/dev.ps1
# macOS / Linux
bash scripts/dev.sh
```

## Environment variables

See [.env.example](.env.example) for the complete list. Never commit `.env`.

Required for a working local slice:

- `DATABASE_URL`
- `REDIS_URL` (or `QUEUE_BACKEND=memory` if Redis is down)
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_API_KEY`
- `CORS_ALLOWED_ORIGINS`
- `NEXT_PUBLIC_API_BASE_URL`

## Database migrations

Always use Alembic. Never change production schema by hand.

```bash
cd services/backend
alembic upgrade head
alembic revision --autogenerate -m "describe the change"
alembic downgrade -1
```

## Tests

```bash
# Backend
cd services/backend
pytest

# Frontend unit tests
cd apps/web
npm run test

# Critical end-to-end (API + web must be running)
cd apps/web
npx playwright test
```

## Ingestion demo (no live crawling)

The first fetcher is a deterministic `demo://` adapter. It never hits the public internet.

1. Open Admin → Sources and create (or use the seeded) `demo://harbor-and-rye` source.
2. Click **Refresh source** (or `POST /api/v1/admin/sources/{id}/refresh`).
3. Inspect the immutable SourceSnapshot.
4. Review the ExtractionCandidate.
5. Approve/publish.
6. The deal appears on the consumer home page and `/api/v1/deals`.

## Deployment

- **Frontend:** Vercel project rooted at `apps/web`.
- **API / worker / cron / Postgres / Key Value:** Render via [render.yaml](render.yaml).

Secrets stay in the Vercel and Render dashboards. See ARCHITECTURE.md for the exact values to set.

## License

Proprietary. All rights reserved.
