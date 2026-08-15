#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f .env ]] || cp .env.example .env
[[ -f apps/web/.env.local ]] || cp apps/web/.env.example apps/web/.env.local
docker compose up -d
echo "Postgres and Redis are up."
echo "Backend:  cd services/backend && source .venv/bin/activate && alembic upgrade head && python -m app.db.seed && uvicorn app.main:app --reload --port 8000"
echo "Worker:   cd services/backend && source .venv/bin/activate && python -m app.workers.runner"
echo "Web:      cd apps/web && npm run dev"
