"""Contract tests between the Android client sources and the live application server.

The Android sources are inspected for the endpoints they call and the payload fields
they read. Every one of those is then exercised against an in-process instance of the
application server so drift between the client and the interface fails the suite even
when the Android toolchain is unavailable.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from api.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[2]
KOTLIN_ROOT = REPO_ROOT / "android/app/src/main/java/com/labrow/browser"
API_CLIENT = KOTLIN_ROOT / "core/ApiClient.kt"
MAPPER = KOTLIN_ROOT / "core/EnvironmentMapper.kt"
REPOSITORY = KOTLIN_ROOT / "core/EnvironmentRepository.kt"
SYNC = KOTLIN_ROOT / "core/SyncController.kt"

OPT_CALL = re.compile(r"opt(?:String|Int|Double|Boolean|Long|JSONObject|JSONArray)\(\s*\"([a-z0-9_]+)\"")
PUT_CALL = re.compile(r"\.put\(\s*\"([a-z0-9_]+)\"")
PATH_LITERAL = re.compile(r"\"(/api/[^\"]*)\"")
QUERY_LITERAL = re.compile(r"\.append\(\"(&?)([a-z_]+)=\"\)")
CALL_SITE = re.compile(r"request\(\s*([^;]*?),\s*\"(GET|POST|PUT|DELETE)\"", re.S)
STATIC_ROUTE = re.compile(r'if path == "(/api/[^"]+)" and method == "([A-Z]+)"')
PROFILE_ROUTE_MARKER = "match = PROFILE_ROUTE.match(path)"

MISSING_VALUE = object()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def request(base_url: str, path: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    target = urllib.request.Request(base_url + path, data=data, method=method)
    target.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(target, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


@pytest.fixture(scope="module")
def live_server():
    server = build_server("127.0.0.1", 0, REPO_ROOT)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def lookup(payload, dotted: str):
    node = payload
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return MISSING_VALUE
        node = node[part]
    return node


def flatten_keys(payload) -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(key)
            keys |= flatten_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            keys |= flatten_keys(item)
    return keys


def normalize_client_path(value: str) -> str:
    path = value.split("?", 1)[0]
    if path.endswith("/"):
        return path + "{id}"
    return path


def server_routes() -> set[tuple[str, str]]:
    source = read(REPO_ROOT / "api/server.py")
    routes = set(STATIC_ROUTE.findall(source))
    dynamic = source.split(PROFILE_ROUTE_MARKER, 1)[1].split("raise ApiError(404", 1)[0]
    for method in re.findall(r'method == "([A-Z]+)"', dynamic):
        routes.add(("/api/profiles/{id}", method))
    return routes


def client_endpoints() -> set[tuple[str, str]]:
    source = read(API_CLIENT)
    endpoints: set[tuple[str, str]] = set()
    for expression, method in CALL_SITE.findall(source):
        if "query.toString()" in expression:
            builder = re.search(r'StringBuilder\("(/api/[^"]*)"', source)
            assert builder is not None
            endpoints.add((normalize_client_path(builder.group(1)), method))
            continue
        for literal in PATH_LITERAL.findall(expression):
            endpoints.add((normalize_client_path(literal), method))
    return endpoints


def test_client_endpoints_are_registered_on_the_server():
    endpoints = client_endpoints()
    routes = server_routes()
    assert len(endpoints) >= 7, sorted(endpoints)
    assert len(routes) >= 15, sorted(routes)
    missing = sorted(endpoints - routes)
    assert missing == [], f"the client calls endpoints the server does not expose: {missing}"
    assert ("/api/health", "GET") in endpoints
    assert ("/api/environment", "GET") in endpoints
    assert ("/api/profiles/{id}", "PUT") in endpoints
    assert ("/api/dns/probe", "POST") in endpoints


def test_client_environment_request_round_trips_through_the_live_server(live_server):
    status, payload = request(live_server, "/api/environment?url=https%3A%2F%2Fexample.com%2F&profile=default&resolver=system")
    assert status == 200
    assert payload["snapshot"]["status"] == "OK"
    status, diagnostics = request(live_server, "/api/diagnostics?level=redacted")
    assert status == 200
    assert diagnostics["report"]["redaction"]["level"] == "redacted"
    status, scans = request(live_server, "/api/scans")
    assert status == 200
    assert {entry["scanner"] for entry in scans["scans"]} == {"emoji", "comment", "english", "branding"}
    profile_id = "android-contract-probe"
    status, saved = request(
        live_server,
        "/api/profiles/" + profile_id,
        "PUT",
        {"profile": {"name": profile_id, "profile_version": 2, "geolocation_mode": "manual", "country": "DE", "city": "Hamburg", "latitude": 53.55, "longitude": 9.99, "radius": 4000, "timezone": "Europe/Berlin", "locale": "de-DE"}},
    )
    assert status == 200
    assert saved["saved"]["id"] == profile_id
    assert saved["profile"]["city"] == "Hamburg"
    status, fetched = request(live_server, "/api/profiles/" + profile_id)
    assert status == 200
    assert fetched["profile"]["city"] == "Hamburg"
    status, removed = request(live_server, "/api/profiles/" + profile_id, "DELETE")
    assert status == 200
    assert removed["id"] == profile_id
    assert removed["deleted"] is True


def test_client_environment_query_parameters_are_honoured(live_server):
    source = read(API_CLIENT)
    parameters = [name for _, name in QUERY_LITERAL.findall(source)]
    assert {"url", "profile", "resolver", "privacy", "private"} <= set(parameters)
    status, payload = request(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.com%2F&profile=default&resolver=system&privacy=strict&private=true",
    )
    assert status == 200
    snapshot = payload["snapshot"]
    assert snapshot["privacy"]["preset"] == "strict"
    assert snapshot["private_browsing"] is True
    assert snapshot["privacy"]["private_browsing"] is True
    assert snapshot["privacy"]["policy"]["cookies"] == "disabled"


def test_every_field_the_mapper_reads_is_present_in_the_live_payload(live_server):
    status, payload = request(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.com%2F&profile=default&resolver=cloudflare-doh&privacy=balanced&private=false",
    )
    assert status == 200
    available = flatten_keys(payload)
    mapped = set(OPT_CALL.findall(read(MAPPER)))
    assert len(mapped) >= 35, sorted(mapped)
    missing = sorted(mapped - available)
    assert missing == [], f"fields read by EnvironmentMapper are absent from the payload: {missing}"


def test_mapper_treats_the_dns_block_as_optional(live_server):
    status, payload = request(live_server, "/api/environment?resolver=system&profile=default")
    assert status == 200
    assert payload["snapshot"]["dns"] is None
    mapper = read(MAPPER)
    assert 'val dnsPayload = snapshot.optJSONObject("dns")' in mapper
    assert "dnsPayload?.let" in mapper


def test_mapped_values_match_the_server_environment(live_server):
    status, payload = request(
        live_server,
        "/api/environment?url=https%3A%2F%2Fexample.com%2F&profile=default&resolver=cloudflare-doh&privacy=balanced&private=false",
    )
    assert status == 200
    snapshot = payload["snapshot"]
    assert lookup(snapshot, "geo.coordinate.latitude") not in (MISSING_VALUE, None)
    assert lookup(snapshot, "geo.mode") == "manual"
    assert lookup(snapshot, "geo.source") == "virtual"
    assert lookup(snapshot, "timezone.zone") == "Europe/Berlin"
    assert lookup(snapshot, "timezone.offset_minutes") == 120
    assert lookup(snapshot, "locale.surfaces.browser_locale") == "en-GB"
    assert lookup(snapshot, "dns.active_resolver") == "Cloudflare DNS over HTTPS"
    assert lookup(snapshot, "dns.resolver_protocol") == "doh"
    assert lookup(snapshot, "dns.tls_status") == "VERIFIED"
    assert lookup(snapshot, "dns.system_resolver_unchanged") is True
    assert lookup(snapshot, "privacy.policy.webrtc_policy") == "privacy_enhanced"
    assert lookup(snapshot, "privacy.preset") == "balanced"
    assert snapshot["consistency"]["findings"]
    for finding in snapshot["consistency"]["findings"]:
        assert {"id", "severity", "message"} <= set(finding)
        assert lookup(snapshot, "state.state") not in (MISSING_VALUE, None)


def test_client_resolver_selection_changes_the_dns_block(live_server):
    status, base = request(live_server, "/api/environment?resolver=system&profile=default")
    assert status == 200
    assert base["snapshot"]["dns"] is None
    status, doh = request(live_server, "/api/environment?resolver=quad9-doh&profile=default")
    assert status == 200
    assert doh["snapshot"]["dns"]["resolver_protocol"] == "doh"
    assert doh["snapshot"]["dns"]["endpoint"].startswith("https")


def environment_document_reader_keys() -> set[str]:
    source = read(REPOSITORY)
    body = source.split("fun environmentDocument", 1)[1].split("fun networkState", 1)[0]
    return set(OPT_CALL.findall(body))


def test_persisted_document_keys_cover_every_reader_field():
    written = set(PUT_CALL.findall(read(SYNC)))
    read_back = environment_document_reader_keys()
    assert len(read_back) >= 25, sorted(read_back)
    missing = sorted(read_back - written)
    assert missing == [], f"EnvironmentRepository reads keys that SyncController never writes: {missing}"


def test_client_base_url_matches_the_application_server_default_port():
    source = read(API_CLIENT)
    assert "10.0.2.2" in source
    envelope = read(REPO_ROOT / ".eng/artifacts/environment.json") if (REPO_ROOT / ".eng/artifacts/environment.json").is_file() else ""
    assert "8000" in source or "8000" in envelope


def test_client_debug_profile_keeps_cleartext_limited_to_the_development_host():
    debug_config = read(REPO_ROOT / "android/app/src/debug/res/xml/network_security_config.xml")
    release_config = read(REPO_ROOT / "android/app/src/main/res/xml/network_security_config.xml")
    assert 'cleartextTrafficPermitted="true"' in debug_config
    assert debug_config.count("cleartextTrafficPermitted=\"true\"") == 1
    for host in ("10.0.2.2", "127.0.0.1", "localhost"):
        assert host in debug_config
    assert "cleartextTrafficPermitted=\"true\"" not in release_config
    assert "10.0.2.2" not in release_config
