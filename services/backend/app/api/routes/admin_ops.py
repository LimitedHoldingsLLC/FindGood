from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.admin_schemas import (
    AuditOut,
    BulkVenuesIn,
    CrawlDomainOut,
    CrawlIn,
    ErrorGroupOut,
    FreshnessBucketOut,
    IngestionRunOut,
    NotesIn,
    OpsDealOut,
    OpsOverviewOut,
    OpsVenueOut,
    PageOut,
    ProviderOut,
    ProviderSearchIn,
    ReviewActionIn,
    ReviewOut,
    SearchOut,
    SystemHealthOut,
)
from app.api.dependencies import admin_principal, ops_service_dep
from app.core.security import Principal
from app.services.ops_service import OpsService

router = APIRouter(prefix="/api/v1/admin", tags=["admin-ops"], dependencies=[Depends(admin_principal)])


@router.get("/overview", response_model=OpsOverviewOut)
def overview(service: OpsService = Depends(ops_service_dep)) -> OpsOverviewOut:
    return service.overview()


@router.get("/search", response_model=SearchOut)
def admin_search(q: str = Query(min_length=1), service: OpsService = Depends(ops_service_dep)) -> SearchOut:
    return service.search(q)


@router.get("/ops/venues", response_model=PageOut)
def ops_venues(
    q: str | None = None,
    city: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: OpsService = Depends(ops_service_dep),
) -> PageOut:
    return service.list_venues(q=q, city=city, page=page, page_size=page_size)


@router.get("/ops/venues/{venue_id}", response_model=OpsVenueOut)
def ops_venue(venue_id: UUID, service: OpsService = Depends(ops_service_dep)) -> OpsVenueOut:
    return service.venue_detail(venue_id)


@router.post("/ops/venues/{venue_id}/disable", response_model=OpsVenueOut)
def disable_venue(
    venue_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> OpsVenueOut:
    return service.disable_venue(venue_id, actor=principal.subject)


@router.post("/ops/venues/{venue_id}/crawl", response_model=IngestionRunOut)
def crawl_venue(
    venue_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.queue_crawl(url=None, venue_id=venue_id, requested_by=principal.subject)


@router.post("/ops/venues/{venue_id}/refresh-google", response_model=IngestionRunOut)
def refresh_google(
    venue_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.refresh_provider("google_places", venue_id, actor=principal.subject)


@router.post("/ops/venues/{venue_id}/refresh-yelp", response_model=IngestionRunOut)
def refresh_yelp(
    venue_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.refresh_provider("yelp", venue_id, actor=principal.subject)


@router.get("/ops/deals", response_model=PageOut)
def ops_deals(
    q: str | None = None,
    freshness: str | None = None,
    city: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: OpsService = Depends(ops_service_dep),
) -> PageOut:
    return service.list_deals(q=q, freshness=freshness, city=city, page=page, page_size=page_size)


@router.get("/ops/deals/{deal_id}", response_model=OpsDealOut)
def ops_deal(deal_id: UUID, service: OpsService = Depends(ops_service_dep)) -> OpsDealOut:
    return service.deal_detail(deal_id)


@router.post("/ops/deals/{deal_id}/verify", response_model=OpsDealOut)
def verify_deal(
    deal_id: UUID,
    payload: NotesIn,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> OpsDealOut:
    return service.verify_deal(deal_id, actor=principal.subject, notes=payload.notes)


@router.post("/ops/deals/{deal_id}/reject", response_model=OpsDealOut)
def reject_deal(
    deal_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> OpsDealOut:
    return service.reject_deal(deal_id, actor=principal.subject)


@router.post("/ops/deals/{deal_id}/expire", response_model=OpsDealOut)
def expire_deal(
    deal_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> OpsDealOut:
    return service.expire_deal(deal_id, actor=principal.subject)


@router.post("/ops/deals/{deal_id}/restore", response_model=OpsDealOut)
def restore_deal(
    deal_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> OpsDealOut:
    return service.restore_deal(deal_id, actor=principal.subject)


@router.post("/ingestion/crawl", response_model=IngestionRunOut)
def ingestion_crawl(
    payload: CrawlIn,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.queue_crawl(
        url=payload.url,
        venue_id=payload.venue_id,
        requested_by=principal.subject,
        sync=payload.sync,
    )


@router.post("/ingestion/google/search", response_model=IngestionRunOut)
def google_search(
    payload: ProviderSearchIn,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.queue_provider_search(
        "google_places",
        text=payload.text,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        requested_by=principal.subject,
        sync=payload.sync,
    )


@router.post("/ingestion/yelp/search", response_model=IngestionRunOut)
def yelp_search(
    payload: ProviderSearchIn,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.queue_provider_search(
        "yelp",
        text=payload.text,
        city=payload.city,
        latitude=payload.latitude,
        longitude=payload.longitude,
        requested_by=principal.subject,
        sync=payload.sync,
    )


@router.post("/ingestion/refresh", response_model=dict)
def ingestion_refresh(
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> dict:
    return service.queue_stale_refresh(requested_by=principal.subject)


@router.get("/ingestion/runs", response_model=PageOut)
def ingestion_runs(
    provider: str | None = None,
    job_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: OpsService = Depends(ops_service_dep),
) -> PageOut:
    return service.list_runs(provider=provider, job_type=job_type, status=status, page=page, page_size=page_size)


@router.get("/ingestion/runs/{run_id}", response_model=IngestionRunOut)
def ingestion_run(run_id: UUID, service: OpsService = Depends(ops_service_dep)) -> IngestionRunOut:
    return service.get_run(run_id)


@router.post("/ingestion/runs/{run_id}/retry", response_model=IngestionRunOut)
def retry_run(
    run_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.retry_run(run_id, requested_by=principal.subject)


@router.post("/ingestion/runs/{run_id}/cancel", response_model=IngestionRunOut)
def cancel_run(
    run_id: UUID,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> IngestionRunOut:
    return service.request_cancel(run_id, requested_by=principal.subject)


@router.get("/providers", response_model=list[ProviderOut])
def providers(service: OpsService = Depends(ops_service_dep)) -> list[ProviderOut]:
    return service.providers()


@router.get("/freshness", response_model=FreshnessBucketOut)
def freshness(
    freshness: str | None = None,
    city: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: OpsService = Depends(ops_service_dep),
) -> FreshnessBucketOut:
    return service.freshness(freshness=freshness, city=city, page=page, page_size=page_size)


@router.post("/freshness/queue-refresh", response_model=dict)
def queue_freshness_refresh(
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> dict:
    return service.queue_stale_refresh(requested_by=principal.subject)


@router.get("/review", response_model=PageOut)
def review_queue(
    status: str | None = "pending",
    page: int = 1,
    page_size: int = 20,
    service: OpsService = Depends(ops_service_dep),
) -> PageOut:
    return service.list_review(status=status, page=page, page_size=page_size)


@router.post("/review/{item_id}", response_model=ReviewOut)
def review_action(
    item_id: UUID,
    payload: ReviewActionIn,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> ReviewOut:
    return service.resolve_review(item_id, action=payload.action, actor=principal.subject)


@router.get("/errors", response_model=list[ErrorGroupOut])
def errors(service: OpsService = Depends(ops_service_dep)) -> list[ErrorGroupOut]:
    return service.errors()


@router.get("/crawler/domains", response_model=list[CrawlDomainOut])
def crawler_domains(service: OpsService = Depends(ops_service_dep)) -> list[CrawlDomainOut]:
    return service.crawl_domains()


@router.get("/system", response_model=SystemHealthOut)
def system_health(service: OpsService = Depends(ops_service_dep)) -> SystemHealthOut:
    return service.system_health()


@router.get("/audit", response_model=list[AuditOut])
def audit(service: OpsService = Depends(ops_service_dep)) -> list[AuditOut]:
    return service.audit()


@router.post("/bulk/crawl", response_model=dict)
def bulk_crawl(
    payload: BulkVenuesIn,
    service: OpsService = Depends(ops_service_dep),
    principal: Principal = Depends(admin_principal),
) -> dict:
    if not payload.confirm:
        return {"queued": 0, "needs_confirmation": True}
    return service.bulk_queue_crawls(payload.venue_ids, actor=principal.subject)


@router.get("/exports/{kind}")
def export_kind(kind: str, service: OpsService = Depends(ops_service_dep)):
    rows = service.export_rows(kind)

    def generate():
        if not rows:
            yield "id\n"
            return
        keys = list(rows[0].keys())
        yield ",".join(keys) + "\n"
        for row in rows:
            yield ",".join(str(row.get(k, "")).replace(",", " ") for k in keys) + "\n"

    return StreamingResponse(generate(), media_type="text/csv")
