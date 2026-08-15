# Starts local infrastructure. Run API, worker, and web in separate terminals.
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path apps\web\.env.local)) { Copy-Item apps\web\.env.example apps\web\.env.local }
docker compose up -d
Write-Host "Postgres and Redis are up."
Write-Host "Backend:  cd services\backend; .venv\Scripts\activate; alembic upgrade head; python -m app.db.seed; uvicorn app.main:app --reload --port 8000"
Write-Host "Worker:   cd services\backend; .venv\Scripts\activate; python -m app.workers.runner"
Write-Host "Web:      cd apps\web; npm run dev"
