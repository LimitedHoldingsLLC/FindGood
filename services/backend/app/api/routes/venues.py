from fastapi import APIRouter, Depends, Query

from app.api.dependencies import venue_service_dep
from app.api.schemas import VenueListOut, VenueOut
from app.domain.taxonomy.verticals import Vertical
from app.services.venue_service import VenueService

router = APIRouter(prefix="/api/v1/venues", tags=["venues"])


@router.get("", response_model=VenueListOut)
def list_venues(
    city: str | None = None,
    neighborhood: str | None = None,
    category: str | None = None,
    vertical: Vertical | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    service: VenueService = Depends(venue_service_dep),
) -> VenueListOut:
    return service.list_venues(
        city=city,
        neighborhood=neighborhood,
        category=category,
        vertical=vertical.value if vertical else None,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=VenueOut)
def get_venue(slug: str, service: VenueService = Depends(venue_service_dep)) -> VenueOut:
    return service.get_by_slug(slug)
