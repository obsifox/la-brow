"""Gecko artifact generation tests."""

from __future__ import annotations

import json

from gecko.integration import PATCH_REQUIRED_SURFACES, integration_plan
from gecko.prefs import render_policies_json, render_user_js, sort_preferences
from privacy.policy import PRESETS


def test_preferences_are_sorted_deterministically():
    ordered = sort_preferences({"network.dns.test": 1, "environment.geo.mode": "manual", "intl.accept_languages": "en"})
    names = [name for name, _ in ordered]
    assert names[0] == "environment.geo.mode"
    assert names[1] == "intl.accept_languages"


def test_user_js_contains_no_comments(profile_payload):
    plan = integration_plan(profile_payload, PRESETS["balanced"], None, None)
    content = plan["user_js"]
    assert chr(47) + chr(47) not in content
    assert content.startswith('user_pref("environment.')
    assert content.endswith(";\n")


def test_boolean_and_numeric_preferences_render_correctly():
    content = render_user_js({"a.true": True, "a.false": False, "a.number": 7, "a.string": "value"})
    assert 'user_pref("a.false", false);' in content
    assert 'user_pref("a.number", 7);' in content
    assert 'user_pref("a.string", "value");' in content


def test_policies_json_dns_over_https_block():
    payload = json.loads(render_policies_json("https://cloudflare-dns.com/dns-query", True))
    block = payload["policies"]["DNSOverHTTPS"]
    assert block["Enabled"] is True
    assert block["ProviderURL"] == "https://cloudflare-dns.com/dns-query"
    assert block["Locked"] is True
    assert block["Fallback"] is False


def test_policies_json_without_endpoint_omits_resolver_policy():
    payload = json.loads(render_policies_json(None, False))
    assert "DNSOverHTTPS" not in payload["policies"]


def test_integration_plan_reports_patch_required_surfaces():
    plan = integration_plan({"name": "x", "geolocation_mode": "manual"}, PRESETS["balanced"], None, None)
    surfaces = {item["surface"] for item in plan["patch_required_surfaces"]}
    assert {"geolocation-provider", "timezone-spoofing", "dns-over-https-policy"} <= surfaces
    assert plan["build_status"] == "scaffolded-not-built"
    assert "not executed" in plan["statement"]
    assert len(PATCH_REQUIRED_SURFACES) == len(plan["patch_required_surfaces"])
