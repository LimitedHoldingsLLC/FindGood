from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import admin_principal, admin_service_dep, queue_dep, settings_dep
from app.api.schemas import (
    CandidateOut,
    CrawlRunOut,
    DealCreateIn,
    DealOut,
    DealUpdateIn,
    ItemCreateIn,
    JobAcceptedOut,
    LocationCreateIn,
    ScheduleCreateIn,
    SnapshotOut,
    SourceCreateIn,
    SourceOut,
    VenueCreateIn,
    VenueOut,
    VenueUpdateIn,
    VerifyIn,
)
from app.core.config import Settings
from app.core.security import Principal
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.publishers.deal import DealPublisher
from app.services.admin_service import AdminService
from app.services.presenters import present_deal, utcnow
from app.workers.queue import JobQueue, enqueue_source_refresh

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(admin_principal)])


@router.get("/venues", response_model=list[VenueOut])
def admin_venues(service: AdminService = Depends(admin_service_dep)) -> list[VenueOut]:
    return service.list_venues()


@router.post("/venues", response_model=VenueOut)
def create_venue(payload: VenueCreateIn, service: AdminService = Depends(admin_service_dep)) -> VenueOut:
    return service.create_venue(payload)


@router.patch("/venues/{venue_id}", response_model=VenueOut)
def update_venue(
    venue_id: UUID, payload: VenueUpdateIn, service: AdminService = Depends(admin_service_dep)
) -> VenueOut:
    return service.update_venue(venue_id, payload)


@router.post("/venues/{venue_id}/locations", response_model=VenueOut)
def add_location(
    venue_id: UUID, payload: LocationCreateIn, service: AdminService = Depends(admin_service_dep)
) -> VenueOut:
    return service.add_location(venue_id, payload)


@router.get("/deals", response_model=list[DealOut])
def admin_deals(service: AdminService = Depends(admin_service_dep)) -> list[DealOut]:
    return service.list_deals()


@router.post("/deals", response_model=DealOut)
def create_deal(payload: DealCreateIn, service: AdminService = Depends(admin_service_dep)) -> DealOut:
    return service.create_deal(payload)


@router.patch("/deals/{deal_id}", response_model=DealOut)
def update_deal(deal_id: UUID, payload: DealUpdateIn, service: AdminService = Depends(admin_service_dep)) -> DealOut:
    return service.update_deal(deal_id, payload)


@router.post("/deals/{deal_id}/schedules", response_model=DealOut)
def add_schedule(
    deal_id: UUID, payload: ScheduleCreateIn, service: AdminService = Depends(admin_service_dep)
) -> DealOut:
    return service.add_schedule(deal_id, payload)


@router.post("/deals/{deal_id}/items", response_model=DealOut)
def add_item(deal_id: UUID, payload: ItemCreateIn, service: AdminService = Depends(admin_service_dep)) -> DealOut:
    return service.add_item(deal_id, payload)


@router.post("/deals/{deal_id}/verify", response_model=DealOut)
def verify_deal(deal_id: UUID, payload: VerifyIn, service: AdminService = Depends(admin_service_dep)) -> DealOut:
    return service.verify_deal(deal_id, payload)


@router.get("/sources", response_model=list[SourceOut])
def admin_sources(service: AdminService = Depends(admin_service_dep)) -> list[SourceOut]:
    return service.list_sources()


@router.post("/sources", response_model=SourceOut)
def create_source(payload: SourceCreateIn, service: AdminService = Depends(admin_service_dep)) -> SourceOut:
    return service.create_source(payload)


@router.post("/sources/{source_id}/disable", response_model=SourceOut)
def disable_source(source_id: UUID, service: AdminService = Depends(admin_service_dep)) -> SourceOut:
    return service.disable_source(source_id)


@router.post("/sources/{source_id}/refresh", response_model=JobAcceptedOut)
def refresh_source(
    source_id: UUID,
    queue: JobQueue = Depends(queue_dep),
    service: AdminService = Depends(admin_service_dep),
) -> JobAcceptedOut:
    service.sources.get(source_id)
    job_id = enqueue_source_refresh(queue, str(source_id))
    return JobAcceptedOut(job_id=job_id, source_id=source_id)


@router.post("/sources/{source_id}/refresh/sync", response_model=CrawlRunOut)
def refresh_source_sync(
    source_id: UUID,
    service: AdminService = Depends(admin_service_dep),
    settings: Settings = Depends(settings_dep),
) -> CrawlRunOut:
    """Synchronous path for local demos when a worker is not running."""
    service.sources.get(source_id)
    run = IngestionPipeline(service.db, settings).run(source_id)
    return CrawlRunOut.model_validate(run)


@router.get("/sources/{source_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(source_id: UUID, service: AdminService = Depends(admin_service_dep)) -> list[SnapshotOut]:
    return service.list_snapshots(source_id)


@router.get("/candidates", response_model=list[CandidateOut])
def list_candidates(
    review_status: str | None = Query(default=None),
    service: AdminService = Depends(admin_service_dep),
) -> list[CandidateOut]:
    return service.list_candidates(review_status)


@router.get("/candidates/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: UUID, service: AdminService = Depends(admin_service_dep)) -> CandidateOut:
    return service.get_candidate(candidate_id)


@router.post("/candidates/{candidate_id}/approve", response_model=DealOut)
def approve_candidate(
    candidate_id: UUID,
    service: AdminService = Depends(admin_service_dep),
    principal: Principal = Depends(admin_principal),
) -> DealOut:
    deal = DealPublisher(service.db, service.flags).publish(candidate_id, actor=principal.subject)
    return present_deal(
        deal,
        now=utcnow(),
        verification=service.deals.latest_verification(deal.id),
        publication=deal.publications[0] if deal.publications else None,
        flags=service.flags,
    )


@router.post("/candidates/{candidate_id}/reject", response_model=CandidateOut)
def reject_candidate(candidate_id: UUID, service: AdminService = Depends(admin_service_dep)) -> CandidateOut:
    return service.reject_candidate(candidate_id)


@router.get("/crawl-runs", response_model=list[CrawlRunOut])
def list_runs(source_id: UUID | None = None, service: AdminService = Depends(admin_service_dep)) -> list[CrawlRunOut]:
    return service.list_runs(source_id)
