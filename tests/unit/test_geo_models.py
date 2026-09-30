"""Geo value object validation tests."""

from __future__ import annotations

import pytest

from geo.errors import InvalidCoordinateError, InvalidRadiusError
from geo.models import GeoCircle, GeoCoordinate, GeoFix, GeoMode, GeoSource, validate_coordinate


def test_valid_coordinate_is_accepted():
    latitude, longitude = validate_coordinate(52.52, 13.405)
    assert (latitude, longitude) == (52.52, 13.405)


@pytest.mark.parametrize(
    "latitude,longitude",
    [(91.0, 0.0), (-91.0, 0.0), (0.0, 181.0), (0.0, -181.0), (float("nan"), 0.0), (float("inf"), 0.0)],
)
def test_invalid_coordinates_are_rejected(latitude, longitude):
    with pytest.raises(InvalidCoordinateError):
        validate_coordinate(latitude, longitude)


def test_non_numeric_coordinate_is_rejected():
    with pytest.raises(InvalidCoordinateError):
        validate_coordinate("52.52", 13.405)


def test_radius_bounds_are_enforced():
    with pytest.raises(InvalidRadiusError):
        GeoCircle(center=GeoCoordinate(52.52, 13.405), radius_m=-1)
    with pytest.raises(InvalidRadiusError):
        GeoCircle(center=GeoCoordinate(52.52, 13.405), radius_m=600000)


def test_confidence_bounds_are_enforced():
    coordinate = GeoCoordinate(52.52, 13.405)
    with pytest.raises(InvalidCoordinateError):
        GeoFix(coordinate=coordinate, source=GeoSource.VIRTUAL, mode=GeoMode.MANUAL, confidence=1.4, timestamp="2026-01-01T00:00:00Z", provider_id="test")
    fix = GeoFix(coordinate=coordinate, source=GeoSource.VIRTUAL, mode=GeoMode.MANUAL, confidence=1.0, timestamp="2026-01-01T00:00:00Z", provider_id="test")
    assert fix.as_dict()["confidence"] == 1.0


def test_rounded_coordinate_limits_precision():
    coordinate = GeoCoordinate(52.520008, 13.404954, accuracy_m=12.4)
    rounded = coordinate.rounded(2)
    assert rounded.latitude == 52.52
    assert rounded.longitude == 13.4
    assert rounded.accuracy_m == 12.0
