"""Tiny geohash encoder for map cache keys.

We do not cache every exact floating-point viewport. Nearby pans should
share a key so Redis does not explode with unique rectangles.
"""

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode(latitude: float, longitude: float, *, precision: int = 5) -> str:
    lat_range = [-90.0, 90.0]
    lng_range = [-180.0, 180.0]
    bits: list[int] = []
    even = True
    while len(bits) < precision * 5:
        if even:
            mid = (lng_range[0] + lng_range[1]) / 2
            if longitude >= mid:
                bits.append(1)
                lng_range[0] = mid
            else:
                bits.append(0)
                lng_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if latitude >= mid:
                bits.append(1)
                lat_range[0] = mid
            else:
                bits.append(0)
                lat_range[1] = mid
        even = not even
    chars: list[str] = []
    for index in range(0, len(bits), 5):
        value = 0
        for bit in bits[index : index + 5]:
            value = (value << 1) | bit
        chars.append(_BASE32[value])
    return "".join(chars)


def precision_for_zoom(zoom: int) -> int:
    if zoom >= 15:
        return 6
    if zoom >= 12:
        return 5
    return 4
