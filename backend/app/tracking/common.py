"""UTC helpers and spherical display coordinates; no orbit propagation."""

import math
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def compass(degrees: float) -> str:
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((degrees + 22.5) // 45) % 8]


def globe_xyz(latitude: float, longitude: float, altitude: float) -> list[float]:
    """Project provider latitude/longitude/height onto the UI's spherical Earth."""
    lat, lon = math.radians(latitude), math.radians(longitude)
    radius = 6378.137 + altitude
    return [
        radius * math.cos(lat) * math.cos(lon),
        radius * math.cos(lat) * math.sin(lon),
        radius * math.sin(lat),
    ]
