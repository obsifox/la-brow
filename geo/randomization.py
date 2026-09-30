"""Deterministic coordinate randomization inside a permitted radius."""

from __future__ import annotations

import hashlib
import random

from geo.errors import InvalidRadiusError
from geo.geodesy import destination_point, haversine_distance_m
from geo.models import GeoCircle, GeoCoordinate, RandomizationDistribution, RandomizationScope

SEED_MODULUS = 2**32


def derive_seed(*parts: str) -> int:
    hasher = hashlib.sha256()
    for part in parts:
        hasher.update(part.encode("utf-8"))
        hasher.update(b"\x1f")
    return int.from_bytes(hasher.digest()[:8], "big") % SEED_MODULUS


def seed_for_scope(
    scope: RandomizationScope,
    base_seed: int | None,
    session_id: str | None,
    profile_id: str | None,
    query_index: int,
) -> tuple[int | None, str]:
    if scope is RandomizationScope.NONE:
        return None, "no-randomization"
    if scope is RandomizationScope.PER_QUERY:
        seed = derive_seed(str(base_seed or 0), session_id or "", profile_id or "", str(query_index))
        return seed, "per-query-seeded"
    if scope is RandomizationScope.PER_SESSION:
        seed = derive_seed(str(base_seed or 0), session_id or "anonymous-session", profile_id or "")
        return seed, "per-session-stable"
    seed = derive_seed(str(base_seed or 0), profile_id or "default-profile")
    return seed, "per-profile-stable"


def sample_coordinate(circle: GeoCircle, seed: int | None) -> GeoCoordinate:
    generator = random.Random(seed)
    if circle.distribution is RandomizationDistribution.CENTER_ONLY or circle.radius_m <= 0:
        return circle.center
    if circle.radius_m <= 0:
        raise InvalidRadiusError("radius must be positive for disk sampling", radius=circle.radius_m)
    radial_fraction = generator.random() ** 0.5
    bearing = generator.uniform(0.0, 360.0)
    distance = radial_fraction * circle.radius_m
    return destination_point(circle.center, bearing, distance)


def sample_verified(circle: GeoCircle, seed: int | None) -> tuple[GeoCoordinate, float]:
    coordinate = sample_coordinate(circle, seed)
    distance = haversine_distance_m(circle.center, coordinate)
    tolerance = max(1.0, circle.radius_m * 1e-6)
    if distance > circle.radius_m + tolerance:
        raise InvalidRadiusError(
            "sampled coordinate exceeds permitted radius",
            radius=circle.radius_m,
            sampled_distance_m=distance,
        )
    return coordinate, distance


def randomization_report(circle: GeoCircle, scope: RandomizationScope, seed: int | None, sample_count: int = 256) -> dict:
    distances = []
    for index in range(sample_count):
        local_seed = None if seed is None else (seed + index) % SEED_MODULUS
        coordinate = sample_coordinate(circle, local_seed)
        distances.append(haversine_distance_m(circle.center, coordinate))
    distances.sort()
    if not distances:
        return {"samples": 0}
    mean = sum(distances) / len(distances)
    variance = sum((value - mean) ** 2 for value in distances) / len(distances)
    return {
        "samples": sample_count,
        "scope": scope.value,
        "radius_m": circle.radius_m,
        "min_distance_m": round(distances[0], 2),
        "max_distance_m": round(distances[-1], 2),
        "mean_distance_m": round(mean, 2),
        "stddev_distance_m": round(variance**0.5, 2),
        "expected_mean_distance_m": round(circle.radius_m * 2.0 / 3.0, 2),
        "max_within_radius": distances[-1] <= circle.radius_m,
    }
