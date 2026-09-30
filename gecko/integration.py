"""Gecko integration plan describing artifacts and required upstream surfaces."""

from __future__ import annotations

from gecko.prefs import render_policies_json, render_user_js, sort_preferences
from locale_engine.gecko_mapping import preference_map as locale_preference_map
from privacy.policy import preference_map as privacy_preference_map
from timezone.gecko_mapping import preference_map as timezone_preference_map
from webrtc.policy import WebRtcPolicy, preferences as webrtc_preferences

PATCH_REQUIRED_SURFACES = (
    {
        "surface": "geolocation-provider",
        "reason": "Gecko resolves coordinates through the operating system provider; override requires an nsIGeolocationProvider implementation.",
        "status": "plan-only",
    },
    {
        "surface": "timezone-spoofing",
        "reason": "Date.getTimezoneOffset and Intl resolved options are not preference controllable in upstream Gecko.",
        "status": "plan-only",
    },
    {
        "surface": "locale-surface",
        "reason": "Locale negotiation is preference controllable; JavaScript locale surfaces require the same override path as timezone.",
        "status": "partial-via-preferences",
    },
    {
        "surface": "dns-over-https-policy",
        "reason": "Enterprise policy covers resolver selection without modifying the operating system.",
        "status": "supported-by-policy",
    },
)

BUILD_STATUS_STATEMENT = (
    "The Gecko build is not executed inside the current engineering environment. "
    "This module produces the preference and policy artifacts that the Gecko build consumes, and records which upstream surfaces require patches."
)


def collect_preferences(profile: dict, privacy, timezone_resolution, locale_resolution) -> dict:
    preferences: dict = {}
    if timezone_resolution is not None:
        preferences.update(timezone_preference_map(timezone_resolution))
    if locale_resolution is not None:
        preferences.update(locale_preference_map(locale_resolution))
    if privacy is not None:
        preferences.update(privacy_preference_map(privacy))
    webrtc_policy = WebRtcPolicy(profile.get("webrtc_policy", WebRtcPolicy.DEFAULT.value))
    preferences.update(webrtc_preferences(webrtc_policy))
    preferences["environment.geo.mode"] = profile.get("geolocation_mode", "manual")
    preferences["environment.geo.country"] = profile.get("country", "")
    preferences["environment.profile.name"] = profile.get("name", "default")
    preferences["environment.transparent.behaviour"] = True
    return preferences


def integration_plan(profile: dict, privacy, timezone_resolution, locale_resolution, doh_endpoint: str | None = None, doh_enabled: bool = False) -> dict:
    preferences = collect_preferences(profile, privacy, timezone_resolution, locale_resolution)
    return {
        "preferences": dict(sort_preferences(preferences)),
        "user_js": render_user_js(preferences),
        "policies_json": render_policies_json(doh_endpoint, doh_enabled),
        "patch_required_surfaces": list(PATCH_REQUIRED_SURFACES),
        "build_status": "scaffolded-not-built",
        "statement": BUILD_STATUS_STATEMENT,
        "documentation_reference": "docs/architecture/gecko-integration.md",
    }
