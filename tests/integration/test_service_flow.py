"""End to end service flow tests."""

from __future__ import annotations

import json
from pathlib import Path

from application.service import EnvironmentService
from diagnostics.redaction import RedactionLevel
from profiles.store import ProfileStore

REPO_ROOT = Path(__file__).resolve().parents[2]


def service() -> EnvironmentService:
    return EnvironmentService(REPO_ROOT)


def test_service_resolves_site_policy_configuration():
    snapshot = service().resolve(url="https://example.com/page")
    assert snapshot["status"] == "OK"
    overrides = snapshot["policy"]["effective_overrides"]
    assert overrides["timezone"] == "Europe/Berlin"
    assert overrides["locale"] == "en-GB"
    assert snapshot["timezone"]["zone"] == "Europe/Berlin"
    assert snapshot["locale"]["surfaces"]["browser_locale"] == "en-GB"


def test_private_browsing_applies_randomization_policy():
    snapshot = service().resolve(url="https://example.com/page", private_browsing=True)
    assert snapshot["policy"]["effective_overrides"]["randomization"] == "per_query"


def test_gecko_artifacts_are_generated_without_source_comments():
    snapshot = service().resolve(url="https://example.com/")
    integration = next(stage for stage in snapshot["stages"] if stage["stage"] == "gecko_integration")
    user_js = integration["output"]["user_js"]
    assert chr(47) * 2 not in user_js
    assert "environment.geo.mode" in user_js
    assert json.loads(integration["output"]["policies_json"])["policies"] is not None


def test_diagnostic_export_is_redacted_by_default():
    report = service().diagnostics_export("redacted")
    assert report["redaction"]["level"] == "redacted"
    assert report["redaction"]["default_level"] == "redacted"
    coordinate = report["environment"]["geo"]["coordinate"]
    assert len(str(coordinate["latitude"]).split(".")[-1]) <= 1


def test_minimal_export_removes_coordinates_and_hostnames():
    report = service().diagnostics_export("minimal")
    assert report["environment"]["geo"]["coordinate"]["latitude"] == "[removed]"
    network = report["environment"]["stages"][6]["output"]["signals"]
    assert network["hostname"] == "[removed]"


def test_profile_round_trip_through_store(tmp_path, profile_payload):
    store = ProfileStore(tmp_path)
    store.save(profile_payload, "integration-profile")
    exported = store.export("integration-profile")
    fresh = ProfileStore(tmp_path.parent / "second")
    result = fresh.import_payload(exported, "integration-copy")
    assert result["activated"] is True
    assert fresh.load("integration-copy")["latitude"] == profile_payload["latitude"]


def test_resolver_profiles_are_available_from_configuration():
    profiles = service().resolver_profiles
    assert "cloudflare-doh" in profiles
    assert profiles["cloudflare-doh"].endpoint.startswith("https://")
    assert profiles["quad9-dot"].port == 853


def test_command_line_summary_exit_code(monkeypatch, capsys):
    from application import cli

    exit_code = cli.main(["environment", "--url", "https://example.com/", "--summary", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["status"] == "OK"
    assert payload["consistency"] in {"CONSISTENT", "POTENTIAL_MISMATCH"}


def test_command_line_profiles_listing(capsys):
    from application import cli

    exit_code = cli.main(["profiles", "list"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["current_version"] == 2
    assert payload["migrations"][0]["from_version"] == 1


def test_command_line_dns_profile_listing(capsys):
    from application import cli

    exit_code = cli.main(["dns", "--list-profiles"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert any(entry["protocol"] == "doh" for entry in payload)
