# Operator guide: ingestion, crawler, and admin dashboard

This is for a technical founder who is not a full-time infrastructure engineer.

## How the dashboard works

Sign in at `/admin` with `ADMIN_USERNAME` / `ADMIN_PASSWORD`. The dashboard talks only to `/api/v1/admin/*`. It does not query Postgres itself.

Think of three pieces:

1. **Ingestion engine** — Google, Yelp, Tripadvisor, OpenTable (placeholder), and the website crawler.
2. **Admin control plane** — the screens you are looking at.
3. **Freshness engine** — decides whether a fact is still trustworthy.

The loop is: observe → prioritize → refresh → verify → review ambiguity → publish.

## How to trigger a crawl

1. Open **Crawler**.
2. Paste a public `https://` restaurant URL.
3. Click **Queue crawl**.
4. The job appears as queued/running. The page polls every few seconds.
5. Open the run to see pages fetched, robots blocks, and offers created.

You can also open a **Business** and click **Crawl website**.

Manual crawls still obey robots.txt, private-IP blocking, rate limits, and page caps.

## How to interpret statuses

| Label | Meaning |
| --- | --- |
| **Fresh** | Recently verified within the window for that data type. |
| **Aging** | Still OK, but due for a check soon. |
| **Stale** | Past the verification window. Not shown to consumers. |
| **Expired** | An explicit end date has passed, or an operator marked it expired. Not shown to consumers. |
| **Unverified** | We have never verified it (common for brand-new or seed rows). |
| **Verification failed** | We tried to check and could not fetch the source. The offer is **not** assumed gone. |
| **Needs review** | A human should look because extraction was unsure or two restaurants might be the same. |

`last_seen_at` means the source still contained this offer on the latest successful look.  
`last_verified_at` means we had enough evidence to treat it as valid. A failed crawl does not update either field.

## How refresh scheduling works

Each venue and offer can store `next_refresh_at`. The hourly cron (`python -m app.workers.enqueue_stale`) enqueues:

- stale website sources
- freshness recompute
- expired-promotion marking

The worker (`python -m app.workers.runner`) does the actual fetching.

## How to investigate crawler failures

1. **Errors** groups failures by category (timeout, robots, 429, parse).
2. Open the **Ingestion run** for the URL.
3. Check robots blocked vs fetch errors.
4. **Crawler → Domain health** shows hosts with failure streaks.
5. **System health** tells you if Redis/Postgres/the worker are up.
6. **Map quality** (`/admin/map`) shows locations missing trustworthy coordinates, geocodes used today, and review actions. Consumer `/map` never geocodes.

## How to retry a job

Open the run → **Retry**. That creates a new queued job. Cancel only works for queued jobs, or asks a running crawl to stop between pages.

## Provider configuration

Set keys in `.env` / Render. The dashboard shows “configured” vs “not configured” and **never** shows the secret.

- `GOOGLE_PLACES_API_KEY` — Google Cloud Places API (New)
- `YELP_API_KEY` — Yelp Fusion
- OpenTable needs an authorized partner feed. A key alone does nothing; scraping OpenTable is out of scope.

## Which dashboard actions cost money

| Action | Cost risk |
| --- | --- |
| Opening / panning `/map` | Maps JavaScript map loads (browser key). No Places or geocode. |
| Google discovery / refresh | Google Places API billing after quota |
| Background geocode (`location.geocode`) | Geocoding API; capped by `MAX_GEOCODES_*` |
| Yelp discovery / refresh | Yelp Fusion quota |
| Tripadvisor discovery / refresh | Tripadvisor Content API quota |
| Website crawl | Mostly your Render/worker time; be polite, not free if you scale workers |
| Queue stale refreshes | Can enqueue many crawls; keep bulk limits |

## Local commands

```bash
docker compose up -d
cd services/backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
# second terminal
python -m app.workers.runner
```

Frontend: `cd apps/web && npm run dev` then http://localhost:3000/admin
