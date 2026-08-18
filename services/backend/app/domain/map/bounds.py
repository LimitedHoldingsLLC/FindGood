"""Viewport rectangles for map queries. No FastAPI, no SQL.

The consumer map asks for restaurants inside the visible rectangle. We
validate that rectangle here so a bad URL cannot scan the whole planet
or break on the antimeridian.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class InvalidBounds(ValueError):
    pass


@dataclass(frozen=True)
class ViewportBounds:
    north: Decimal
    south: Decimal
    east: Decimal
    west: Decimal

    @property
    def crosses_antimeridian(self) -> bool:
        return self.west > self.east

    @property
    def lat_span(self) -> Decimal:
        return self.north - self.south

    @property
    def lng_span(self) -> Decimal:
        if self.crosses_antimeridian:
            return (Decimal("180") - self.west) + (self.east - Decimal("-180"))
        return self.east - self.west

    def contains(self, latitude: Decimal, longitude: Decimal) -> bool:
        if latitude < self.south or latitude > self.north:
            return False
        if self.crosses_antimeridian:
            return longitude >= self.west or longitude <= self.east
        return self.west <= longitude <= self.east

    def too_wide_for_pins(self, *, max_lat_span: Decimal = Decimal("1.2")) -> bool:
        """World-scale views should cluster / ask the user to zoom, not dump pins."""
        return self.lat_span > max_lat_span or self.lng_span > max_lat_span * 2


def parse_bounds(*, north: Decimal, south: Decimal, east: Decimal, west: Decimal) -> ViewportBounds:
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        raise InvalidBounds("Latitude must be between -90 and 90")
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise InvalidBounds("Longitude must be between -180 and 180")
    if north <= south:
        raise InvalidBounds("north must be greater than south")
    return ViewportBounds(north=north, south=south, east=east, west=west)
