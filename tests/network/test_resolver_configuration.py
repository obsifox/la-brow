"""Resolver configuration and policy tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from dns.engine import load_provider_profiles
from dns.models import ResolverProtocol

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_provider_profiles_load_from_configuration():
    profiles = load_provider_profiles(REPO_ROOT)
    identifiers = set(profiles)
    assert {"system", "cloudflare-doh", "quad9-doh", "cloudflare-dot", "quad9-dot"} <= identifiers
    assert profiles["system"].protocol is ResolverProtocol.SYSTEM
    assert profiles["cloudflare-doh"].protocol is ResolverProtocol.DOH
    assert profiles["cloudflare-dot"].port == 853


def test_encrypted_profiles_require_tls_validation():
    profiles = load_provider_profiles(REPO_ROOT)
    for profile in profiles.values():
        if profile.protocol in {ResolverProtocol.DOH, ResolverProtocol.DOT}:
            assert profile.verify_tls is True


def test_configuration_forbids_operating_system_wide_changes():
    payload = yaml.safe_load((REPO_ROOT / "config/network/dns-providers.yaml").read_text(encoding="utf-8"))
    assert payload["policy"]["os_wide_changes"] == "forbidden"
    assert payload["policy"]["telemetry"] == "none"
    assert payload["default_fallback"]["explicit_confirmation_required"] is True


def test_safe_defaults_declare_no_unexpected_virtualization():
    payload = yaml.safe_load((REPO_ROOT / "config/browser/defaults.yaml").read_text(encoding="utf-8"))
    defaults = payload["safe_defaults"]
    assert defaults["geo_mode"] == "automatic"
    assert defaults["doh_enabled"] is False
    assert defaults["virtual_mode_gps_fallback"] == "forbidden"
    assert defaults["os_wide_dns_modification"] == "forbidden"
    assert defaults["diagnostics_default_export"] == "redacted"
