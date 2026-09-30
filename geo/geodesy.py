"""Geodesic helpers used by radius resolution and diagnostics."""

from __future__ import annotations

import math

from geo.models import EARTH_MEAN_RADIUS_M, GeoCoordinate, validate_coordinate


def to_radians(value: float) -> float:
    return value * math.pi / 180.0


def to_degrees(value: float) -> float:
    return value * 180.0 / math.pi


def haversine_distance_m(first: GeoCoordinate, second: GeoCoordinate) -> float:
    delta_latitude = to_radians(second.latitude - first.latitude)
    delta_longitude = to_radians(second.longitude - first.longitude)
    latitude_first = to_radians(first.latitude)
    latitude_second = to_radians(second.latitude)
    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_first) * math.cos(latitude_second) * math.sin(delta_longitude / 2) ** 2
    )
    return 2.0 * EARTH_MEAN_RADIUS_M * math.asin(min(1.0, math.sqrt(haversine)))


def destination_point(origin: GeoCoordinate, bearing_deg: float, distance_m: float) -> GeoCoordinate:
    angular_distance = distance_m / EARTH_MEAN_RADIUS_M
    bearing = to_radians(bearing_deg)
    latitude = to_radians(origin.latitude)
    longitude = to_radians(origin.longitude)
    target_latitude = math.asin(
        math.sin(latitude) * math.cos(angular_distance) + math.cos(latitude) * math.sin(angular_distance) * math.cos(bearing)
    )
    target_longitude = longitude + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(latitude),
        math.cos(angular_distance) - math.sin(latitude) * math.sin(target_latitude),
    )
    normalized_longitude = (to_degrees(target_longitude) + 540.0) % 360.0 - 180.0
    latitude_degrees, longitude_degrees = validate_coordinate(to_degrees(target_latitude), normalized_longitude)
    return GeoCoordinate(
        latitude=latitude_degrees,
        longitude=longitude_degrees,
        accuracy_m=origin.accuracy_m,
        altitude_m=origin.altitude_m,
        heading_deg=origin.heading_deg,
        speed_mps=origin.speed_mps,
    )


def bounding_box(center: GeoCoordinate, radius_m: float) -> dict:
    latitude_delta = to_degrees(radius_m / EARTH_MEAN_RADIUS_M)
    cosine = math.cos(to_radians(center.latitude))
    longitude_delta = 180.0 if abs(cosine) < 1e-12 else to_degrees(radius_m / (EARTH_MEAN_RADIUS_M * abs(cosine)))
    minimum_latitude = max(-90.0, center.latitude - latitude_delta)
    maximum_latitude = min(90.0, center.latitude + latitude_delta)
    minimum_longitude = max(-180.0, center.longitude - longitude_delta)
    maximum_longitude = min(180.0, center.longitude + longitude_delta)
    return {
        "min_latitude": round(minimum_latitude, 6),
        "max_latitude": round(maximum_latitude, 6),
        "min_longitude": round(minimum_longitude, 6),
        "max_longitude": round(maximum_longitude, 6),
        "crosses_antimeridian": minimum_longitude < -180.0 + 1e-9 or maximum_longitude > 180.0 - 1e-9,
    }
