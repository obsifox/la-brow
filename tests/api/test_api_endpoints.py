"""Application programming interface tests against a live in-process server."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from api.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[2]


def request(base_url: str, path: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    target = urllib.request.Request(base_url + path, data=data, method=method)
    target.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(target, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read().decode("utf-8"))
        return error.code, payload


@pytest.fixture(scope="module")
def live_server():
    server = build_server("127.0.0.1", 0, REPO_ROOT)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    yield base_url
    server.shutdown()
    server.server_close()


def test_health_reports_capabilities(live_server):
    status, payload = request(live_server, "/api/health")
    assert status == 200
    assert payload["status"] == "OK"
    assert payload["profile_version"] == 2
    assert "environment_resolution" in payload["capabilities"]


def test_environment_endpoint_runs_pipeline(live_server):
    status, payload = request(live_server, "/api/environment?url=https://example.com/&profile=default&resolver=system")
    assert status == 200
    snapshot = payload["snapshot"]
    assert snapshot["status"] == "OK"
    assert len(snapshot["stages"]) == 11
    assert snapshot["geo"]["source"] == "virtual"
    assert snapshot["timezone"]["zone"] == "Europe/Berlin"


def test_environment_rejects_unknown_profile(live_server):
    status, payload = request(live_server, "/api/environment?profile=missing-profile")
    assert status == 404
    assert payload["error"]["code"] in {"profile_not_found", "profile_store_error"}


def test_profile_lifecycle_over_http(live_server):
    profile = {
        "name": "http-created",
        "profile_version": 2,
        "geolocation_mode": "manual",
        "country": "NL",
        "city": "Amsterdam",
        "latitude": 52.3676,
        "longitude": 4.9041,
        "radius": 4000,
        "randomization": "per_session",
        "randomization_seed": 11,
        "timezone": "Europe/Amsterdam",
        "locale": "nl-NL",
        "languages": ["nl-NL", "en-US"],
        "webrtc_policy": "privacy_enhanced",
    }
    status, payload = request(live_server, "/api/profiles/http-created", "PUT", {"profile": profile})
    assert status == 200
    assert payload["saved"]["id"] == "http-created"

    status, listing = request(live_server, "/api/profiles")
    assert status == 200
    assert any(entry["id"] == "http-created" for entry in listing["profiles"])

    status, loaded = request(live_server, "/api/profiles/http-created")
    assert status == 200
    assert loaded["profile"]["city"] == "Amsterdam"

    status, resolved = request(live_server, "/api/environment?profile=http-created&url=https://example.org/")
    assert status == 200
    assert resolved["snapshot"]["timezone"]["zone"] == "Europe/Amsterdam"
    assert resolved["snapshot"]["locale"]["surfaces"]["browser_locale"] == "nl-NL"

    status, exported = request(live_server, "/api/profiles/http-created/export")
    assert status == 200
    assert json.loads(exported["payload"])["integrity"]["algorithm"] == "sha256"

    status, deleted = request(live_server, "/api/profiles/http-created", "DELETE")
    assert status == 200
    assert deleted["deleted"] is True


def test_profile_validation_endpoint_reports_problems(live_server):
    status, payload = request(live_server, "/api/profiles/validate", "POST", {"profile": {"name": "bad", "profile_version": 2, "latitude": 200.0, "longitude": 10.0}})
    assert status == 200
    assert payload["status"] == "INVALID"

    status, valid = request(live_server, "/api/profiles/validate", "POST", {"profile": {"name": "good", "profile_version": 2, "latitude": 52.0, "longitude": 13.0}})
    assert valid["status"] == "VALID"


def test_profile_import_rejects_path_traversal(live_server):
    payload_text = json.dumps({"name": "escape", "profile_version": 2, "radius": 0})
    status, payload = request(live_server, "/api/profiles/import", "POST", {"payload": payload_text, "profile_id": "../escape"})
    assert status == 400
    assert payload["error"]["code"] == "profile_store_error"


def test_profile_import_dry_run_does_not_activate(live_server):
    payload_text = json.dumps({"name": "migrating", "profile_version": 1, "randomization": True, "country": "SE", "radius": 0})
    status, payload = request(live_server, "/api/profiles/import", "POST", {"payload": payload_text, "dry_run": True})
    assert status == 200
    assert payload["activated"] is False
    assert payload["migrations_applied"][0]["to_version"] == 2


def test_resolvers_endpoint_lists_profiles(live_server):
    status, payload = request(live_server, "/api/resolvers")
    assert status == 200
    identifiers = {entry["id"] for entry in payload["resolvers"]}
    assert {"system", "cloudflare-doh", "quad9-dot"} <= identifiers


def test_dns_diagnostics_reports_isolation(live_server):
    status, payload = request(live_server, "/api/dns/diagnostics?resolver=system")
    assert status == 200
    assert payload["integrity"]["system_resolver_modified"] is False
    assert payload["diagnostics"]["system_resolver_unchanged"] is True


def test_dns_probe_rejects_unknown_resolver(live_server):
    status, payload = request(live_server, "/api/dns/probe", "POST", {"resolver": "missing", "name": "example.com", "type": "A"})
    assert status == 404
    assert payload["error"]["code"] == "resolver_not_found"


def test_diagnostics_levels_and_redaction(live_server):
    status, payload = request(live_server, "/api/diagnostics?level=minimal")
    assert status == 200
    assert payload["level"] == "minimal"
    assert payload["report"]["environment"]["geo"]["coordinate"]["latitude"] == "[removed]"

    status, failure = request(live_server, "/api/diagnostics?level=unknown")
    assert status == 400
    assert failure["error"]["code"] == "invalid_level"


def test_settings_round_trip(live_server):
    status, payload = request(live_server, "/api/settings")
    assert status == 200
    original = payload["settings"]
    updated = dict(original, default_url="https://example.net/", privacy_preset="strict")
    status, saved = request(live_server, "/api/settings", "PUT", {"settings": updated})
    assert status == 200
    assert saved["settings"]["default_url"] == "https://example.net/"
    request(live_server, "/api/settings", "PUT", {"settings": original})


def test_identity_and_scans_endpoints(live_server):
    status, payload = request(live_server, "/api/identity")
    assert status == 200
    assert payload["report"]["policy"]["contains_text"] is False
    assert payload["assets"]["icon"].startswith("<?xml")

    status, scans = request(live_server, "/api/scans")
    assert status == 200
    assert len(scans["scans"]) == 4


def test_webrtc_endpoint_states_the_limit(live_server):
    status, payload = request(live_server, "/api/webrtc")
    assert status == 200
    assert any("do not guarantee network anonymity" in entry["limitation_statement"] for entry in payload["policies"])


def test_events_endpoint_returns_structured_events(live_server):
    status, payload = request(live_server, "/api/events?url=https://example.com/")
    assert status == 200
    names = [event["name"] for event in payload["events"]]
    assert "environment.pipeline.started" in names


def test_request_log_records_traffic(live_server):
    status, payload = request(live_server, "/api/requests")
    assert status == 200
    assert payload["requests"]
    assert all("path" in entry for entry in payload["requests"])


def test_unknown_route_returns_structured_error(live_server):
    status, payload = request(live_server, "/api/does-not-exist")
    assert status == 404
    assert payload["error"]["code"] == "not_found"


def test_static_client_is_served(live_server):
    with urllib.request.urlopen(live_server + "/", timeout=30) as response:
        markup = response.read().decode("utf-8")
        assert response.status == 200
        assert "LA Brow" in markup
        assert "/ui/app.js" in markup
    with urllib.request.urlopen(live_server + "/ui/app.js", timeout=30) as response:
        script = response.read().decode("utf-8")
        assert response.headers["Content-Type"].startswith("text/javascript")
        assert "api(" in script
    with urllib.request.urlopen(live_server + "/assets/identity/icon.svg", timeout=30) as response:
        assert response.headers["Content-Type"] == "image/svg+xml"


def test_path_traversal_on_static_is_refused(live_server):
    status, payload = request(live_server, "/../../etc/passwd")
    assert status == 404
    assert payload["error"]["code"] == "not_found"


THEME_MANIFEST = {
    "manifest_version": 2,
    "name": "Neon Grid",
    "version": "1.2.0",
    "type": "theme",
    "theme": {
        "colors": {
            "frame": "#05060A",
            "toolbar": "#12142B",
            "tab_selected": ["#FF2D3F", "#A855F7"],
            "toolbar_text": "#F5F7FF",
        },
        "images": {"theme_frame": "header.png"},
    },
}

ADDON_MANIFEST = {
    "manifest_version": 3,
    "name": "Reader Helper",
    "version": "1.0.0",
    "permissions": ["storage", "tabs"],
    "action": {"default_title": "Reader"},
}


@pytest.fixture()
def clean_extensions(live_server):
    import shutil

    extensions_root = REPO_ROOT / "var/extensions"
    shutil.rmtree(extensions_root, ignore_errors=True)
    yield live_server
    shutil.rmtree(extensions_root, ignore_errors=True)


def test_compat_matrix_lists_runtime_surfaces(live_server):
    status, payload = request(live_server, "/api/compat/firefox-desktop")
    assert status == 200
    assert payload["runtime"]["engine"] == "geckoview"
    assert len(payload["sections"]) >= 10
    assert payload["install_notice"].startswith("This add-on targets desktop Firefox")
    assert isinstance(payload["installed"]["count"], int)
    assert payload["installed"]["signature_state"] in {"verified", "unverified"}


def test_theme_manifest_is_inspected_and_translated(clean_extensions):
    status, payload = request(clean_extensions, "/api/extensions/inspect", "POST", {"manifest": THEME_MANIFEST})
    assert status == 200
    assert payload["compatibility"]["level"] == "PARTIAL"
    assert payload["theme"]["gradient"]["stops"][0] == "#05060A"
    assert payload["theme"]["gradient"]["accent"] == "#FF2D3F"
    assert payload["install_preview"]["code"] == "notice_not_acknowledged"


def test_install_requires_the_compatibility_notice(clean_extensions):
    status, payload = request(clean_extensions, "/api/extensions/install", "POST", {"manifest": ADDON_MANIFEST})
    assert status == 409
    assert payload["error"]["code"] == "notice_not_acknowledged"
    status, payload = request(
        clean_extensions,
        "/api/extensions/install",
        "POST",
        {"manifest": ADDON_MANIFEST, "acknowledged": True},
    )
    assert status == 201
    record = payload["installed"]
    assert record["notice_acknowledged"] is True
    assert payload["notice"].startswith("This add-on targets desktop Firefox")
    status, listing = request(clean_extensions, "/api/extensions")
    assert status == 200
    assert listing["count"] == 1
    assert listing["extensions"][0]["name"] == "Reader Helper"


def test_theme_activation_and_removal(clean_extensions):
    status, payload = request(
        clean_extensions,
        "/api/extensions/install",
        "POST",
        {"manifest": THEME_MANIFEST, "acknowledged": True},
    )
    assert status == 201
    identifier = payload["installed"]["id"]
    assert identifier == "neon-grid-1-2-0"
    status, themes = request(clean_extensions, "/api/themes")
    assert status == 200
    assert themes["active_theme"]["id"] == identifier
    assert themes["active_theme"]["gradient"]["stops"][2] == "#FF2D3F"
    status, activated = request(clean_extensions, "/api/themes/active", "PUT", {"id": identifier})
    assert status == 200
    assert activated["active_theme"] == identifier
    status, removed = request(clean_extensions, "/api/extensions/" + identifier, "DELETE")
    assert status == 200
    assert removed["removed"] is True
    status, listing = request(clean_extensions, "/api/extensions")
    assert listing["count"] == 0


def test_prohibited_permission_is_refused(clean_extensions):
    manifest = {**ADDON_MANIFEST, "permissions": ["storage", "nativeMessaging"]}
    status, payload = request(
        clean_extensions,
        "/api/extensions/install",
        "POST",
        {"manifest": manifest, "acknowledged": True},
    )
    assert status == 409
    assert payload["error"]["code"] == "prohibited_permission"
    assert "nativeMessaging" in payload["error"]["detail"]["permissions"]


def test_invalid_manifest_is_reported(clean_extensions):
    status, payload = request(clean_extensions, "/api/extensions/inspect", "POST", {"manifest": {"name": "Broken"}})
    assert status == 400
    assert payload["error"]["code"] == "manifest_invalid"
