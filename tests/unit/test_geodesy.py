"""Geodesic helper tests."""

from __future__ import annotations

from geo.geodesy import bounding_box, destination_point, haversine_distance_m
from geo.models import GeoCoordinate

BERLIN = GeoCoordinate(52.52, 13.405)
PARIS = GeoCoordinate(48.8566, 2.3522)


def test_distance_between_known_cities():
    distance_km = haversine_distance_m(BERLIN, PARIS) / 1000.0
    assert 870 < distance_km < 890


def test_destination_point_respects_requested_distance():
    target = destination_point(BERLIN, 90.0, 1000.0)
    assert 995 < haversine_distance_m(BERLIN, target) < 1005


def test_destination_point_crosses_antimeridian():
    origin = GeoCoordinate(0.0, 179.99)
    target = destination_point(origin, 90.0, 5000.0)
    assert -180.0 <= target.longitude <= 180.0
    assert target.longitude < 0


def test_bounding_box_flags_antimeridian_crossing():
    box = bounding_box(GeoCoordinate(0.0, 179.999), 50000.0)
    assert box["crosses_antimeridian"] is True
    assert -90 <= box["min_latitude"] <= box["max_latitude"] <= 90


def test_polar_bounding_box_is_clamped():
    box = bounding_box(GeoCoordinate(89.9, 0.0), 100000.0)
    assert box["max_latitude"] <= 90
