# FindGood ingestion

Ingestion is how untrusted external content becomes **candidates**. Publishing to the consumer catalog is a separate, explicit step.

A failed crawl must not take down the consumer API. Cron **only enqueues**. The worker runs the pipeline.

## Lifecycle (shipped)

```text
cron / admin refresh
  → enqueue_source_refresh(source_id)
  → worker
      1. open CrawlRun
      2. Fetcher.fetch(url)           # bytes + HTTP metadata only
      3. persist SourceSnapshot       # immutable evidence
      4. Parser.parse(...)
      5. Extractor.extract(...)       # candidates, not live deals
      6. Normalizer.normalize(...)
      7. Validator.validate(...)      # reject / quarantine
      8. persist ExtractionCandidate  # review_status=pending
      9. close CrawlRun
  → admin or trusted publisher
     10. Publisher.publish(candidate) # explicit
```

Crawler output never becomes consumer-facing without step 10.

## Protocols

Defined in `services/backend/app/ingestion/protocols.py`:

| Protocol | May do | Must not do |
| --- | --- | --- |
| `Fetcher` | Return bytes, status, content type | Parse, extract, write deals |
| `Parser` | Structure bytes | Decide what a deal is |
| `Extractor` | Emit `ExtractedCandidate` dicts | Publish |
| `Normalizer` | Canonicalize fields | Hit the network |
| `Validator` | Return error codes | Insert published deals |
| `Publisher` | Create deal + items + schedules + publication + verification | Fetch URLs |

An LLM extractor later implements the same `Extractor` protocol. Do not fork the pipeline for AI.

## What is implemented today

| Adapter | Behavior |
| --- | --- |
| `DemoFetcher` | Reads in-repo JSON fixtures for `demo://…` URLs. Never hits the internet. |
| `HttpFetcher` | Public HTTP(S) GET with size/timeout caps. Must pass `safety.assert_public_http_url`. |
| `JsonParser` | Parses JSON documents only. |
| `DemoExtractor` | Maps demo fixture shapes to deal candidates. |
| `DealNormalizer` / `DealValidator` | Title, schedule, money, confidence. |
| `DealPublisher` | Admin approve path. Requires a `venue_location_id`. |

`IngestionPipeline` currently **constructs these adapters directly**. Root `ARCHITECTURE.md` mentions a registry; that registry is not shipped. When a second real adapter exists, register fetchers/parsers/extractors in one place. Do not add a registry as ceremony.

## Safety

Every network fetch goes through `ingestion/safety.py`:

- `http` / `https` only
- No credentials in the URL
- DNS resolve; block private, loopback, link-local, reserved, multicast
- Block `localhost`, `*.local`, cloud metadata hosts
- Timeout and max bytes from settings
- Source must be `is_active` and `crawl_enabled`

Treat fetched content as untrusted input. Text inside a restaurant page must never change control flow, prompts, or publish rules.

Do not bypass auth, CAPTCHAs, or access controls. Do not scrape private content.

## Jobs

| Job | Who enqueues | Who runs |
| --- | --- | --- |
| `source.refresh` | Admin `POST /sources/{id}/refresh` or stale cron | Worker |
| `sources.enqueue_stale` | Render cron hourly | Cron process, then worker |

Admin also has `POST /sources/{id}/refresh/sync` for local demos when a worker is not running. Production should use the queue.

Retries: up to 5 attempts, then dead-letter. Idempotency key `source.refresh:{source_id}` (one hour on Redis).

## Adding an adapter (when a real source exists)

1. Implement the existing protocols. Put HTML/PDF/social code in new modules under `app/ingestion/`, not in routes or the food app.
2. Do not put extraction in a fetcher.
3. Persist a snapshot before parse. Never update a snapshot in place (including `parser_version` after insert — that write is a known leak to fix later, not a pattern to copy).
4. Unit-test with a fixture. Do not crawl a live site to prove the adapter.
5. Keep publish explicit.

## What ingestion is not

- Not a per-vertical microservice
- Not allowed to write `publication_state=published` from a fetcher
- Not a place for FindGood.food UI
- Not an excuse to store a second copy of the business graph
