from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import deal_service_dep
from app.api.schemas import DealListOut, DealOut
from app.domain.taxonomy.discovery import Cuisine, DrinkKind, TimeBucket, VenueFeature
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
    q: str | None = Query(default=None, max_length=120),
    cuisine: Cuisine | None = None,
    price_level: int | None = Query(default=None, ge=1, le=4),
    drink: DrinkKind | None = None,
    reservations: bool | None = None,
    feature: VenueFeature | None = None,
    when: TimeBucket | None = None,
    day: int | None = Query(default=None, ge=1, le=7),
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
        q=q,
        cuisine=cuisine.value if cuisine else None,
        price_level=price_level,
        drink_kind=drink.value if drink else None,
        accepts_reservations=reservations,
        feature=feature.value if feature else None,
        when=when,
        weekday=day,
        page=page,
        page_size=page_size,
    )


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: UUID, service: DealService = Depends(deal_service_dep)) -> DealOut:
    return service.get_deal(deal_id)
