"""Geo providers implementing physical, virtual, automatic, hybrid and disabled behaviour."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from geo.dataset import country_entry, country_for_locale, country_for_timezone
from geo.errors import ProviderUnavailableError
from geo.geodesy import haversine_distance_m
from geo.models import (
    GeoCircle,
    GeoCoordinate,
    GeoFix,
    GeoMode,
    GeoRequest,
    GeoSource,
    RandomizationScope,
    utc_now_iso,
)
from geo.randomization import sample_verified, seed_for_scope
from network.detection import DetectionSignals, signal_confidence

AUTOMATIC_BASE_ACCURACY_M = 200000.0
AUTOMATIC_BASE_CONFIDENCE = 0.3


class PhysicalLocationBridge(Protocol):
    """Operating system geolocation boundary usable by the physical provider only."""

    def available(self) -> bool:
        ...

    def read_fix(self) -> GeoCoordinate:
        ...


class GeoProvider(ABC):
    provider_id: str
    source: GeoSource
    mode: GeoMode

    @abstractmethod
    def resolve(self, request: GeoRequest) -> GeoFix:
        ...


class DisabledProvider(GeoProvider):
    provider_id = "disabled-provider"
    source = GeoSource.DISABLED
    mode = GeoMode.DISABLED

    def resolve(self, request: GeoRequest) -> GeoFix:
        raise ProviderUnavailableError("geo resolution is disabled by configuration", provider=self.provider_id)


class PhysicalProvider(GeoProvider):
    provider_id = "physical-provider"
    source = GeoSource.PHYSICAL
    mode = GeoMode.AUTOMATIC

    def __init__(self, bridge: PhysicalLocationBridge | None = None) -> None:
        self.bridge = bridge

    def resolve(self, request: GeoRequest) -> GeoFix:
        if self.bridge is None or not self.bridge.available():
            raise ProviderUnavailableError(
                "no physical location bridge is registered",
                provider=self.provider_id,
                detail="operating system geolocation is unavailable to the browser scope",
            )
        coordinate = self.bridge.read_fix()
        return GeoFix(
            coordinate=coordinate,
            source=self.source,
            mode=self.mode,
            confidence=0.9,
            timestamp=utc_now_iso(),
            provider_id=self.provider_id,
            signals=("physical-bridge",),
            notes=("physical provider used only when the active mode permits it",),
        )


class VirtualProvider(GeoProvider):
    provider_id = "virtual-provider"
    source = GeoSource.VIRTUAL
    mode = GeoMode.MANUAL

    def __init__(self, circle: GeoCircle, base_seed: int | None = None) -> None:
        self.circle = circle
        self.base_seed = base_seed
        self.query_index = 0

    def resolve(self, request: GeoRequest) -> GeoFix:
        seed, seed_note = seed_for_scope(
            request.randomization_scope,
            self.base_seed,
            request.session_id,
            request.profile_id,
            self.query_index,
        )
        self.query_index += 1
        coordinate, distance = sample_verified(self.circle, seed)
        return GeoFix(
            coordinate=coordinate,
            source=self.source,
            mode=GeoMode.MANUAL,
            confidence=1.0,
            timestamp=utc_now_iso(),
            provider_id=self.provider_id,
            signals=("virtual-mode", seed_note),
            notes=(f"sampled at {round(distance, 1)} m from profile center inside the permitted radius",),
            seed=seed,
        )


@dataclass
class AutomaticRequest:
    signals: DetectionSignals
    timezone_hint: str | None = None
    locale_hint: str | None = None


class AutomaticProvider(GeoProvider):
    provider_id = "automatic-provider"
    source = GeoSource.AUTOMATIC
    mode = GeoMode.AUTOMATIC

    def __init__(self, request_source: AutomaticRequest | None = None) -> None:
        self.request_source = request_source

    def proposal(self) -> dict:
        if self.request_source is None:
            raise ProviderUnavailableError(
                "automatic detection requires environment signals",
                provider=self.provider_id,
            )
        notes: list[str] = []
        country_code = None
        entry = None
        if self.request_source.timezone_hint:
            match = country_for_timezone(self.request_source.timezone_hint)
            if match is not None:
                country_code, entry = match
                notes.append(f"timezone-hint:{self.request_source.timezone_hint}")
        if country_code is None and self.request_source.locale_hint:
            match = country_for_locale(self.request_source.locale_hint)
            if match is not None:
                country_code, entry = match
                notes.append(f"locale-region-hint:{self.request_source.locale_hint}")
        base_confidence, signal_notes = signal_confidence(self.request_source.signals)
        notes.extend(signal_notes)
        if entry is None or country_code is None:
            raise ProviderUnavailableError(
                "no geographic signal is available for an automatic proposal",
                provider=self.provider_id,
                notes=notes,
            )
        confidence = min(0.6, AUTOMATIC_BASE_CONFIDENCE + base_confidence)
        return {
            "country_code": country_code,
            "country_name": entry["name"],
            "coordinate": GeoCoordinate(
                latitude=entry["latitude"],
                longitude=entry["longitude"],
                accuracy_m=AUTOMATIC_BASE_ACCURACY_M,
            ),
            "timezone": entry.get("timezone"),
            "locales": entry.get("locales", []),
            "confidence": round(confidence, 3),
            "notes": notes,
        }

    def resolve(self, request: GeoRequest) -> GeoFix:
        proposal = self.proposal()
        return GeoFix(
            coordinate=proposal["coordinate"],
            source=self.source,
            mode=GeoMode.AUTOMATIC,
            confidence=proposal["confidence"],
            timestamp=utc_now_iso(),
            provider_id=self.provider_id,
            signals=tuple(proposal["notes"]),
            notes=(
                "automatic proposal is derived from coarse environment signals",
                "the proposal is not a measurement of the user physical position",
            ),
        )


class HybridProvider(GeoProvider):
    provider_id = "hybrid-provider"
    source = GeoSource.HYBRID
    mode = GeoMode.HYBRID

    def __init__(self, automatic: AutomaticProvider, overrides: dict) -> None:
        self.automatic = automatic
        self.overrides = overrides

    def resolve(self, request: GeoRequest) -> GeoFix:
        proposal = self.automatic.proposal()
        notes = [f"automatic-base:{proposal['country_code']}", *proposal["notes"]]
        coordinate = proposal["coordinate"]
        accuracy = coordinate.accuracy_m
        confidence = proposal["confidence"]
        if "latitude" in self.overrides and "longitude" in self.overrides:
            coordinate = GeoCoordinate(
                latitude=float(self.overrides["latitude"]),
                longitude=float(self.overrides["longitude"]),
                accuracy_m=float(self.overrides.get("accuracy_m", accuracy)),
            )
            notes.append("manual-coordinate-override")
            confidence = min(1.0, confidence + 0.3)
        if "radius_m" in self.overrides:
            notes.append(f"manual-radius-override:{self.overrides['radius_m']}")
        if "city" in self.overrides:
            notes.append(f"manual-city-override:{self.overrides['city']}")
        if self.overrides.get("conflict"):
            notes.append("manual-override-conflicts-with-detected-environment")
        return GeoFix(
            coordinate=coordinate,
            source=self.source,
            mode=GeoMode.HYBRID,
            confidence=round(confidence, 3),
            timestamp=utc_now_iso(),
            provider_id=self.provider_id,
            signals=tuple(notes),
            notes=(
                "every automatic decision is reported alongside manual overrides",
                "hybrid mode never hides which fields were set manually",
            ),
        )


def circle_from_profile(profile: dict) -> GeoCircle:
    latitude = profile.get("latitude")
    longitude = profile.get("longitude")
    if latitude is None or longitude is None:
        country = profile.get("country")
        entry = country_entry(country) if country else None
        if entry is None:
            raise ProviderUnavailableError(
                "profile does not define coordinates or a known country",
                profile=profile.get("name"),
            )
        latitude = entry["latitude"]
        longitude = entry["longitude"]
    center = GeoCoordinate(
        latitude=float(latitude),
        longitude=float(longitude),
        accuracy_m=float(profile.get("accuracy_m") or profile.get("radius") or 1000),
    )
    return GeoCircle(center=center, radius_m=float(profile.get("radius") or 0))


def distance_from_center(circle: GeoCircle, coordinate: GeoCoordinate) -> float:
    return haversine_distance_m(circle.center, coordinate)


def default_scope(profile: dict) -> RandomizationScope:
    value = profile.get("randomization")
    if not value:
        return RandomizationScope.NONE
    try:
        return RandomizationScope(value)
    except ValueError:
        return RandomizationScope.NONE
