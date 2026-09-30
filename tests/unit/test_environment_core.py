"""Environment pipeline integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from environment.core import STAGE_ORDER, EnvironmentConfig, EnvironmentCore
from geo.models import GeoMode
from policy.models import PolicyScope, SiteRule

REPO_ROOT = Path(__file__).resolve().parents[2]


def base_profile() -> dict:
    return {
        "name": "pipeline-test",
        "profile_version": 2,
        "geolocation_mode": "manual",
        "country": "DE",
        "city": "Berlin",
        "latitude": 52.52,
        "longitude": 13.405,
        "radius": 3000,
        "accuracy_m": 3000,
        "randomization": "per_session",
        "randomization_seed": 777,
        "timezone": "Europe/Berlin",
        "locale": "de-DE",
        "languages": ["de-DE", "de"],
        "webrtc_policy": "privacy_enhanced",
    }


def run_pipeline(**overrides) -> dict:
    profile = base_profile()
    profile.update(overrides.pop("profile", {}))
    config = EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=False, **overrides)
    return EnvironmentCore(config).run()


def test_pipeline_stage_order_is_deterministic():
    first = run_pipeline()["stage_order"]
    second = run_pipeline()["stage_order"]
    assert first == second == list(STAGE_ORDER)


def test_successful_pipeline_reports_every_stage():
    snapshot = run_pipeline()
    statuses = {stage["stage"]: stage["status"] for stage in snapshot["stages"]}
    assert snapshot["status"] == "OK"
    assert statuses["geo_resolution"] == "OK"
    assert statuses["timezone_resolution"] == "OK"
    assert statuses["locale_resolution"] == "OK"
    assert statuses["dns_resolution"] == "SKIPPED"
    assert statuses["gecko_integration"] == "OK"


def test_virtual_mode_coordinate_is_inside_radius():
    snapshot = run_pipeline()
    coordinate = snapshot["geo"]["coordinate"]
    from geo.geodesy import haversine_distance_m
    from geo.models import GeoCoordinate

    distance = haversine_distance_m(GeoCoordinate(latitude=52.52, longitude=13.405), GeoCoordinate(latitude=coordinate["latitude"], longitude=coordinate["longitude"]))
    assert distance <= 3000
    assert snapshot["geo"]["source"] == "virtual"
    assert snapshot["geo"]["seed"] is not None


def test_manual_mode_without_location_fails_and_halts():
    profile = {"name": "broken", "profile_version": 2, "geolocation_mode": "manual", "randomization": "none"}
    snapshot = EnvironmentCore(EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=False)).run()
    assert snapshot["status"] == "FAILED"
    assert snapshot["halted"] is True
    geo_stage = next(stage for stage in snapshot["stages"] if stage["stage"] == "geo_resolution")
    assert geo_stage["status"] == "SKIPPED"
    validation = next(stage for stage in snapshot["stages"] if stage["stage"] == "environment_validation")
    assert validation["status"] == "FAILED"
    assert validation["output"]["problems"][0]["field"] == "location"


def test_manual_mode_rejecting_physical_fallback_flag():
    profile = base_profile()
    profile["block_physical_fallback"] = False
    snapshot = EnvironmentCore(EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=False)).run()
    validation = next(stage for stage in snapshot["stages"] if stage["stage"] == "environment_validation")
    assert validation["status"] == "FAILED"
    assert any(problem["field"] == "block_physical_fallback" for problem in validation["output"]["problems"])


def test_automatic_mode_with_signals_produces_low_confidence_fix():
    profile = {"name": "auto", "profile_version": 2, "geolocation_mode": "automatic", "timezone": "Europe/Berlin", "locale": "de-DE", "randomization": "none"}
    snapshot = EnvironmentCore(EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=True)).run()
    assert snapshot["status"] == "OK"
    assert snapshot["geo"]["source"] == "automatic"
    assert snapshot["geo"]["confidence"] <= 0.6
    assert snapshot["geo"]["coordinate"]["accuracy_m"] >= 100000


def test_hybrid_mode_reports_manual_overrides():
    profile = dict(base_profile(), geolocation_mode="hybrid", city="Hamburg", radius=1000)
    snapshot = EnvironmentCore(EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=False)).run()
    assert snapshot["geo"]["source"] == "hybrid"
    assert any(signal.startswith("manual-city-override") for signal in snapshot["geo"]["signals"])


def test_validation_rejects_randomization_without_radius():
    profile = dict(base_profile(), radius=0, randomization="per_query")
    snapshot = EnvironmentCore(EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=False)).run()
    validation = next(stage for stage in snapshot["stages"] if stage["stage"] == "environment_validation")
    assert validation["status"] == "FAILED"


def test_invalid_profile_halts_before_geo_resolution():
    profile = dict(base_profile(), latitude=200.0)
    snapshot = EnvironmentCore(EnvironmentConfig(profile=profile, repo_path=REPO_ROOT, detect_network=False)).run()
    assert snapshot["status"] == "FAILED"
    first = snapshot["stages"][0]
    assert first["stage"] == "profile_resolution"
    assert first["status"] == "FAILED"


def test_site_policy_overrides_reach_effective_profile():
    rule = SiteRule(id="t", scope=PolicyScope.DOMAIN, pattern="example.com", overrides={"timezone": "Asia/Tokyo"}, priority=5)
    snapshot = EnvironmentCore(
        EnvironmentConfig(profile=base_profile(), site_rules=[rule], repo_path=REPO_ROOT, detect_network=False)
    ).run(url="https://example.com/")
    assert snapshot["effective_profile"]["timezone"] == "Asia/Tokyo"
    assert snapshot["timezone"]["zone"] == "Asia/Tokyo"


def test_events_are_emitted_without_sensitive_payloads():
    snapshot = run_pipeline()
    names = [event["name"] for event in snapshot["events"]]
    assert "environment.pipeline.started" in names
    assert "geo.changed" in names
    assert "timezone.changed" in names
    assert all("token" not in str(event["payload"]).lower() for event in snapshot["events"])


def test_invariants_are_evaluated():
    snapshot = run_pipeline()
    stage = next(stage for stage in snapshot["stages"] if stage["stage"] == "web_content_ready")
    identifiers = {item["id"] for item in stage["output"]["invariants"]}
    assert {"virtual-mode-without-physical-fallback", "browser-scoped-dns", "public-ip-unchanged", "no-anonymity-claim"} <= identifiers
    assert all(item["satisfied"] for item in stage["output"]["invariants"])


def test_pipeline_state_machine_records_history():
    snapshot = run_pipeline()
    history = snapshot["state"]["history"]
    assert history[0]["to"] == "UNKNOWN"
    assert any(entry["to"] == "MANUAL" for entry in history)
