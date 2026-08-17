from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import deal_service_dep
from app.api.schemas import DealListOut, DealOut
from app.domain.taxonomy.verticals import Vertical
from app.services.deal_service import DealService

router = APIRouter(prefix="/api/v1/deals", tags=["deals"])


@router.get("", response_model=DealListOut)
def list_deals(
    city: str | None = None,
    neighborhood: str | None = None,
    category: str | None = None,
    offering_kind: str | None = Query(default=None, alias="food_or_drink"),
    deal_type: str | None = None,
    vertical: Vertical | None = None,
    max_price: Decimal | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
    radius_km: float | None = Query(default=None, alias="radius"),
    active_now: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    service: DealService = Depends(deal_service_dep),
) -> DealListOut:
    return service.list_deals(
        city=city,
        neighborhood=neighborhood,
        category=category,
        offering_kind=offering_kind,
        deal_type=deal_type,
        vertical=vertical.value if vertical else None,
        max_price=max_price,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        active_now=active_now,
        page=page,
        page_size=page_size,
    )


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: UUID, service: DealService = Depends(deal_service_dep)) -> DealOut:
    return service.get_deal(deal_id)
