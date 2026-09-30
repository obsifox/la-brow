"""Verify that the keys the android client reads exist in live server payloads."""

from __future__ import annotations

import json
import re
import threading
import urllib.request
from pathlib import Path

import pytest

from api.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPER_SOURCE = REPO_ROOT / "android/app/src/main/java/com/labrow/browser/core/EnvironmentMapper.kt"
CLIENT_SOURCE = REPO_ROOT / "android/app/src/main/java/com/labrow/browser/core/ApiClient.kt"
ACCESS = re.compile(r'opt(?:String|Int|Long|Double|Boolean|JSONObject|JSONArray)\("([^"]+)"')


@pytest.fixture(scope="module")
def live_server():
    server = build_server("127.0.0.1", 0, REPO_ROOT)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def fetch(base_url: str, path: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base_url + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_keys(node, collected: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            collected.add(key)
            collect_keys(value, collected)
    elif isinstance(node, list):
        for entry in node:
            collect_keys(entry, collected)


def test_client_endpoints_answer(live_server):
    source = CLIENT_SOURCE.read_text(encoding="utf-8")
    paths = sorted(set(re.findall(r'request\("(/api/[^"]*)"', source)))
    assert len(paths) >= 14
    replies = {
        "/api/health": fetch(live_server, "/api/health"),
        "/api/profiles": fetch(live_server, "/api/profiles"),
        "/api/resolvers": fetch(live_server, "/api/resolvers"),
        "/api/settings": fetch(live_server, "/api/settings"),
        "/api/extensions": fetch(live_server, "/api/extensions"),
        "/api/themes": fetch(live_server, "/api/themes"),
        "/api/scans": fetch(live_server, "/api/scans"),
        "/api/compat/firefox-desktop": fetch(live_server, "/api/compat/firefox-desktop"),
        "/api/diagnostics?level=redacted": fetch(live_server, "/api/diagnostics?level=redacted"),
    }
    for path, payload in replies.items():
        assert isinstance(payload, dict), path
        assert payload, path
    assert {"status", "version", "capabilities"} <= set(replies["/api/health"])
    registry = replies["/api/extensions"]
    assert {"extensions", "themes", "count", "notice", "signature_state", "runtime"} <= set(registry)
    assert "may not display" in registry["notice"]
    matrix = replies["/api/compat/firefox-desktop"]
    assert matrix["runtime"]["engine_version"]
    assert len(matrix["sections"]) >= 15
    assert "may not display" in matrix["install_notice"]
    assert replies["/api/resolvers"]["resolvers"]
    assert replies["/api/diagnostics?level=redacted"]["report"]


def test_environment_keys_match_the_android_mapper(live_server):
    payload = fetch(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.com%2Fpage&profile=default&resolver=cloudflare-doh&privacy=strict&private=true",
    )
    supplied: set[str] = set()
    collect_keys(payload, supplied)
    referenced = sorted(set(ACCESS.findall(MAPPER_SOURCE.read_text(encoding="utf-8"))))
    missing = [key for key in referenced if key not in supplied]
    assert missing == [], f"mapper reads keys the server does not send: {missing}"


def test_system_resolver_leaves_browser_dns_unset(live_server):
    payload = fetch(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.org%2F&profile=default&resolver=system&privacy=balanced&private=false",
    )
    snapshot = payload["snapshot"]
    assert snapshot["dns"] is None
    dns_stage = {stage["stage"]: stage for stage in snapshot["stages"]}["dns_resolution"]
    assert dns_stage["status"] == "SKIPPED"


def test_invariant_count_source_stage_carries_invariants(live_server):
    payload = fetch(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.com%2Fpage&profile=default&resolver=system&privacy=balanced&private=false",
    )
    snapshot = payload["snapshot"]
    stages = {stage["stage"]: stage for stage in snapshot["stages"]}
    assert "web_content_ready" in stages
    invariants = stages["web_content_ready"]["output"]["invariants"]
    assert invariants
    assert all(entry["satisfied"] is True for entry in invariants)
    assert len(invariants) >= 4


def test_privacy_preset_and_private_browsing_are_reported(live_server):
    payload = fetch(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.com%2Fpage&profile=default&resolver=system&privacy=strict&private=true",
    )
    snapshot = payload["snapshot"]
    assert snapshot["privacy"]["preset"] == "strict"
    assert snapshot["privacy"]["private_browsing"] is True
    assert snapshot["private_browsing"] is True
