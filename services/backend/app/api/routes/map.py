from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import map_service_dep
from app.api.schemas import MapListOut
from app.db.models.enums import DealType
from app.domain.taxonomy.discovery import Cuisine, MapWhen
from app.domain.taxonomy.verticals import Vertical
from app.services.map_service import MapService

router = APIRouter(prefix="/api/v1/map", tags=["map"])


@router.get("/locations", response_model=MapListOut)
def list_map_locations(
    north: Decimal = Query(..., ge=-90, le=90),
    south: Decimal = Query(..., ge=-90, le=90),
    east: Decimal = Query(..., ge=-180, le=180),
    west: Decimal = Query(..., ge=-180, le=180),
    zoom: int = Query(12, ge=1, le=21),
    q: str | None = Query(default=None, max_length=120),
    offering_kind: str | None = Query(default=None, alias="food_or_drink"),
    deal_type: str | None = None,
    cuisine: Cuisine | None = None,
    price_level: int | None = Query(default=None, ge=1, le=4),
    when: MapWhen | None = None,
    day: int | None = Query(default=None, ge=1, le=7),
    vertical: Vertical | None = None,
    service: MapService = Depends(map_service_dep),
) -> MapListOut:
    # The map only asks our backend for restaurants inside the visible
    # rectangle. This prevents us from sending every FindGood restaurant
    # to the browser as the database grows.
    if deal_type is not None:
        try:
            DealType(deal_type)
        except ValueError:
            from app.core.exceptions import ValidationFailed

            raise ValidationFailed("Unknown deal type") from None
    return service.list_pins(
        north=north,
        south=south,
        east=east,
        west=west,
        zoom=zoom,
        q=q,
        offering_kind=offering_kind,
        deal_type=deal_type,
        cuisine=cuisine.value if cuisine else None,
        price_level=price_level,
        when=when.value if when else None,
        weekday=day,
        vertical=vertical.value if vertical else None,
    )
