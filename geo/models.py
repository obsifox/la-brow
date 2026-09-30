"""Value objects for geographic resolution."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone as timezone_module
from enum import Enum

from geo.errors import InvalidCoordinateError, InvalidRadiusError

EARTH_MEAN_RADIUS_M = 6371008.8
MAX_ACCURACY_M = 500000.0
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
MAX_RADIUS_M = 500000.0


class GeoMode(str, Enum):
    DISABLED = "disabled"
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    HYBRID = "hybrid"


class GeoSource(str, Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    AUTOMATIC = "automatic"
    HYBRID = "hybrid"
    DISABLED = "disabled"


class RandomizationScope(str, Enum):
    NONE = "none"
    PER_QUERY = "per_query"
    PER_SESSION = "per_session"
    PER_PROFILE = "per_profile"


class RandomizationDistribution(str, Enum):
    UNIFORM_DISK = "uniform_disk"
    CENTER_ONLY = "center_only"


def utc_now_iso() -> str:
    return datetime.now(timezone_module.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_coordinate(latitude: float, longitude: float) -> tuple[float, float]:
    if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
        raise InvalidCoordinateError("latitude must be numeric", latitude=latitude)
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
        raise InvalidCoordinateError("longitude must be numeric", longitude=longitude)
    if math.isnan(latitude) or math.isnan(longitude):
        raise InvalidCoordinateError("coordinates must not be NaN")
    if math.isinf(latitude) or math.isinf(longitude):
        raise InvalidCoordinateError("coordinates must be finite")
    if latitude < MIN_LATITUDE or latitude > MAX_LATITUDE:
        raise InvalidCoordinateError("latitude out of range", latitude=latitude)
    if longitude < MIN_LONGITUDE or longitude > MAX_LONGITUDE:
        raise InvalidCoordinateError("longitude out of range", longitude=longitude)
    return float(latitude), float(longitude)


def validate_radius(radius_m: float) -> float:
    if not isinstance(radius_m, (int, float)) or isinstance(radius_m, bool):
        raise InvalidRadiusError("radius must be numeric", radius=radius_m)
    if math.isnan(radius_m) or math.isinf(radius_m):
        raise InvalidRadiusError("radius must be finite", radius=radius_m)
    if radius_m < 0:
        raise InvalidRadiusError("radius must not be negative", radius=radius_m)
    if radius_m > MAX_RADIUS_M:
        raise InvalidRadiusError("radius exceeds supported maximum", radius=radius_m, maximum=MAX_RADIUS_M)
    return float(radius_m)


def validate_accuracy(accuracy_m: float) -> float:
    if accuracy_m <= 0 or accuracy_m > MAX_ACCURACY_M:
        raise InvalidCoordinateError("accuracy out of range", accuracy=accuracy_m, maximum=MAX_ACCURACY_M)
    return float(accuracy_m)


@dataclass(frozen=True)
class GeoCoordinate:
    latitude: float
    longitude: float
    accuracy_m: float = 1000.0
    altitude_m: float | None = None
    heading_deg: float | None = None
    speed_mps: float | None = None

    def __post_init__(self) -> None:
        validate_coordinate(self.latitude, self.longitude)
        validate_accuracy(self.accuracy_m)
        if self.altitude_m is not None and not -12000.0 <= self.altitude_m <= 100000.0:
            raise InvalidCoordinateError("altitude out of range", altitude=self.altitude_m)
        if self.heading_deg is not None and not 0.0 <= self.heading_deg < 360.0:
            raise InvalidCoordinateError("heading out of range", heading=self.heading_deg)
        if self.speed_mps is not None and self.speed_mps < 0:
            raise InvalidCoordinateError("speed must not be negative", speed=self.speed_mps)

    def as_dict(self) -> dict:
        return asdict(self)

    def rounded(self, decimals: int = 2) -> "GeoCoordinate":
        return GeoCoordinate(
            latitude=round(self.latitude, decimals),
            longitude=round(self.longitude, decimals),
            accuracy_m=round(self.accuracy_m, 0),
            altitude_m=None if self.altitude_m is None else round(self.altitude_m, 0),
            heading_deg=None if self.heading_deg is None else round(self.heading_deg, 1),
            speed_mps=None if self.speed_mps is None else round(self.speed_mps, 1),
        )


@dataclass(frozen=True)
class GeoCircle:
    center: GeoCoordinate
    radius_m: float = 0.0
    distribution: RandomizationDistribution = RandomizationDistribution.UNIFORM_DISK

    def __post_init__(self) -> None:
        validate_radius(self.radius_m)

    def as_dict(self) -> dict:
        return {
            "center": self.center.as_dict(),
            "radius_m": self.radius_m,
            "distribution": self.distribution.value,
        }


@dataclass(frozen=True)
class GeoFix:
    coordinate: GeoCoordinate
    source: GeoSource
    mode: GeoMode
    confidence: float
    timestamp: str
    provider_id: str
    signals: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    seed: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidCoordinateError("confidence must be within 0 and 1", confidence=self.confidence)

    def as_dict(self) -> dict:
        return {
            "coordinate": self.coordinate.as_dict(),
            "source": self.source.value,
            "mode": self.mode.value,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
            "provider_id": self.provider_id,
            "signals": list(self.signals),
            "notes": list(self.notes),
            "seed": self.seed,
        }


@dataclass
class GeoRequest:
    mode: GeoMode
    circle: GeoCircle | None = None
    randomization_scope: RandomizationScope = RandomizationScope.NONE
    block_physical_fallback: bool = True
    session_id: str | None = None
    profile_id: str | None = None
    conflict_signals: tuple[str, ...] = ()
    context: dict = field(default_factory=dict)
