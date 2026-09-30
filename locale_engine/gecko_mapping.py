"""Mapping between locale resolution and Gecko integration surfaces."""

from __future__ import annotations

from locale_engine.models import LocaleResolution


def preference_map(resolution: LocaleResolution) -> dict:
    return {
        "intl.accept_languages": resolution.http_language_preference.replace(",", ", "),
        "intl.locale.requested": resolution.browser_locale,
        "general.useragent.locale": resolution.browser_locale,
        "javascript.use_us_english_locale": resolution.browser_locale.lower().startswith("en-us"),
        "environment.locale.mode": resolution.mode.value,
    }


def integration_report(resolution: LocaleResolution) -> dict:
    return {
        "preferences": preference_map(resolution),
        "surfaces": resolution.surface_map(),
        "notes": list(resolution.notes),
        "documentation_reference": "docs/architecture/geo-architecture.md",
        "limitation_statement": "Locale control covers browser preferences, HTTP language negotiation and JavaScript locale surfaces exposed through browser controlled APIs.",
    }
