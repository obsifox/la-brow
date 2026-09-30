"""Value objects for browser scoped timezone configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TimezoneMode(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    PROFILE = "profile"
    DISABLED = "disabled"


@dataclass(frozen=True)
class TimezoneConfig:
    mode: TimezoneMode
    zone: str | None = None
    source_profile: str | None = None
    allow_dst_spoofing: bool = True


@dataclass(frozen=True)
class TimezoneResolution:
    zone: str
    mode: TimezoneMode
    offset_minutes: int
    dst_active: bool
    abbreviation: str
    confidence: float
    source: str
    controlled_surfaces: tuple[str, ...]
    uncontrolled_surfaces: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "zone": self.zone,
            "mode": self.mode.value,
            "offset_minutes": self.offset_minutes,
            "dst_active": self.dst_active,
            "abbreviation": self.abbreviation,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "controlled_surfaces": list(self.controlled_surfaces),
            "uncontrolled_surfaces": list(self.uncontrolled_surfaces),
            "notes": list(self.notes),
        }
