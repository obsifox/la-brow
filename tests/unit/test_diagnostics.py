"""Diagnostics consistency and redaction tests."""

from __future__ import annotations

from diagnostics.consistency import check
from diagnostics.redaction import RedactionLevel, redact, redact_ip


def sample_inputs():
    profile = {"country": "DE", "latitude": 52.52, "longitude": 13.405}
    geo_fix = {"coordinate": {"latitude": 52.5, "longitude": 13.4, "accuracy_m": 5000}, "source": "virtual"}
    timezone_resolution = {"zone": "Asia/Tokyo", "offset_minutes": 540}
    locale_resolution = {"surfaces": {"browser_locale": "en-US"}}
    dns_status = {"resolver_protocol": "system", "system_resolver_unchanged": True}
    return profile, geo_fix, timezone_resolution, locale_resolution, dns_status


def test_timezone_and_locale_mismatches_are_reported():
    result = check(*sample_inputs())
    identifiers = {finding["id"] for finding in result["findings"]}
    assert "timezone-location-mismatch" in identifiers
    assert "locale-region-mismatch" in identifiers
    assert result["status"] == "POTENTIAL_MISMATCH"
    assert result["statement"].startswith("Consistency diagnostics")


def test_consistent_environment_reports_no_findings():
    profile, geo_fix, _, _, dns_status = sample_inputs()
    result = check(profile, geo_fix, {"zone": "Europe/Berlin", "offset_minutes": 120}, {"surfaces": {"browser_locale": "de-DE"}}, dns_status)
    assert result["findings"] == []
    assert result["status"] == "CONSISTENT"


def test_encrypted_resolver_declaration_mismatch_is_high_severity():
    profile, geo_fix, timezone_resolution, locale_resolution, _ = sample_inputs()
    profile = dict(profile, doh="cloudflare-doh")
    result = check(profile, geo_fix, timezone_resolution, locale_resolution, {"resolver_protocol": "system", "system_resolver_unchanged": True})
    finding = next(item for item in result["findings"] if item["id"] == "resolver-mode-declared-but-not-active")
    assert finding["severity"] == "HIGH"
    assert result["highest_severity"] == "HIGH"


def test_modified_system_resolver_is_high_severity():
    profile, geo_fix, timezone_resolution, locale_resolution, dns_status = sample_inputs()
    result = check(profile, geo_fix, timezone_resolution, locale_resolution, dict(dns_status, system_resolver_unchanged=False))
    assert any(item["id"] == "system-resolver-modified" and item["severity"] == "HIGH" for item in result["findings"])


def test_coordinate_distance_finding():
    profile = {"country": "DE", "latitude": 35.68, "longitude": 139.69}
    geo_fix = {"coordinate": {"latitude": 35.68, "longitude": 139.69}}
    result = check(profile, geo_fix, None, None, None)
    assert any(item["id"] == "coordinate-country-distance" for item in result["findings"])


def test_ip_redaction_forms():
    assert redact_ip("192.168.1.55") == "192.168.x.x"
    assert redact_ip("2606:4700:4700::1111").startswith("2606:4700:")
    assert redact_ip("not-an-address") == "[redacted]"


def test_redaction_levels_differ_on_coordinates_and_hosts():
    document = {
        "geo": {"latitude": 52.520008, "longitude": 13.404954},
        "network": {"resolver_addresses": ["192.168.1.1"], "hostname": "sandbox-host"},
        "auth": {"token": "secret-value"},
    }
    full = redact(document, RedactionLevel.FULL)
    redacted = redact(document, RedactionLevel.REDACTED)
    minimal = redact(document, RedactionLevel.MINIMAL)
    assert full["network"]["resolver_addresses"] == ["192.168.1.1"]
    assert redacted["network"]["resolver_addresses"] == ["192.168.x.x"]
    assert redacted["geo"]["latitude"] == 52.5
    assert minimal["geo"]["latitude"] == "[removed]"
    assert minimal["network"]["hostname"] == "[removed]"
    assert full["auth"]["token"] == "[removed]"
    assert redacted["redaction"]["default_level"] == "redacted"
