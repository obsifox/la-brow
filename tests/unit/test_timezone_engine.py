"""Timezone engine tests covering offsets, daylight saving and validation."""

from __future__ import annotations

from datetime import datetime, timezone as timezone_module

import pytest

from timezone.engine import dst_transition_table, is_valid_zone, normalize_zone, resolve, zone_offset
from timezone.errors import InvalidTimezoneError
from timezone.models import TimezoneConfig, TimezoneMode

WINTER = datetime(2026, 1, 15, 12, 0, tzinfo=timezone_module.utc)
SUMMER = datetime(2026, 7, 15, 12, 0, tzinfo=timezone_module.utc)


@pytest.mark.parametrize("zone", ["UTC", "Europe/Berlin", "Asia/Tokyo", "America/New_York", "Australia/Sydney"])
def test_known_zones_are_valid(zone):
    assert is_valid_zone(zone) is True


def test_unknown_zone_is_rejected():
    assert is_valid_zone("Mars/Olympus") is False
    with pytest.raises(InvalidTimezoneError):
        normalize_zone("Mars/Olympus")


def test_alias_is_normalized():
    assert normalize_zone("GMT") == "Etc/GMT"


def test_utc_offset_is_zero():
    offset, dst_active, abbreviation = zone_offset(WINTER, "UTC")
    assert offset == 0
    assert dst_active is False
    assert abbreviation == "UTC"


def test_positive_and_negative_offsets():
    tokyo_offset, _, _ = zone_offset(WINTER, "Asia/Tokyo")
    new_york_offset, _, _ = zone_offset(WINTER, "America/New_York")
    assert tokyo_offset == 540
    assert new_york_offset == -300


def test_daylight_saving_transition_detected():
    winter_offset, winter_dst, _ = zone_offset(WINTER, "Europe/Berlin")
    summer_offset, summer_dst, _ = zone_offset(SUMMER, "Europe/Berlin")
    assert winter_offset == 60
    assert summer_offset == 120
    assert winter_dst is False
    assert summer_dst is True


def test_zone_without_daylight_saving():
    transitions = dst_transition_table("Asia/Tokyo", 2026)
    assert transitions == []


def test_dst_zone_transition_table_has_two_entries():
    transitions = dst_transition_table("Europe/Berlin", 2026)
    assert len(transitions) == 2
    offsets = sorted(entry["offset_minutes"] for entry in transitions)
    assert offsets == [60, 120]


def test_manual_mode_requires_zone():
    with pytest.raises(InvalidTimezoneError):
        resolve(TimezoneConfig(mode=TimezoneMode.MANUAL), None)


def test_automatic_mode_requires_detected_zone():
    with pytest.raises(Exception):
        resolve(TimezoneConfig(mode=TimezoneMode.AUTOMATIC), None)


def test_manual_resolution_reports_controlled_surfaces():
    resolution = resolve(TimezoneConfig(mode=TimezoneMode.MANUAL, zone="Europe/Berlin"), None, moment=SUMMER)
    payload = resolution.as_dict()
    assert payload["zone"] == "Europe/Berlin"
    assert "javascript-date-offset" in payload["controlled_surfaces"]
    assert "operating-system-clock" in payload["uncontrolled_surfaces"]
    assert payload["confidence"] == 1.0
