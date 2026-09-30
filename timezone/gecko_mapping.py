"""Mapping between timezone resolution and Gecko integration surfaces."""

from __future__ import annotations

from timezone.models import TimezoneResolution

GECKO_PREF_TEMPLATE = {
    "javascript.use_us_english_locale": False,
    "privacy.resistFingerprinting": False,
}

PATCH_REQUIRED_SURFACES = (
    "nsIDOMWindowUtils timezone override hook",
    "Date.getTimezoneOffset override inside the environment content script",
    "Intl.DateTimeFormat resolvedOptions override inside the environment content script",
)


def preference_map(resolution: TimezoneResolution) -> dict:
    return {
        **GECKO_PREF_TEMPLATE,
        "environment.timezone.zone": resolution.zone,
        "environment.timezone.offset_minutes": resolution.offset_minutes,
        "environment.timezone.mode": resolution.mode.value,
        "environment.timezone.controlled": "true",
    }


def integration_report(resolution: TimezoneResolution) -> dict:
    return {
        "zone": resolution.zone,
        "preferences": preference_map(resolution),
        "patch_required": list(PATCH_REQUIRED_SURFACES),
        "controlled_surfaces": list(resolution.controlled_surfaces),
        "uncontrolled_surfaces": list(resolution.uncontrolled_surfaces),
        "documentation_reference": "docs/architecture/geo-architecture.md",
        "limitation_statement": "Browser scoped timezone control covers JavaScript and Intl surfaces inside the browser only; the operating system clock and other applications are unchanged.",
    }
