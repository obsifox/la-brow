"""Locale engine tests covering distinguishable surfaces."""

from __future__ import annotations

from locale_engine.engine import build_accept_language, resolve
from locale_engine.models import LocaleConfig, LocaleMode


def test_manual_locale_resolution_surfaces_are_distinct():
    resolution = resolve(LocaleConfig(mode=LocaleMode.MANUAL, locale="en-GB", languages=("en-GB", "de-DE")), "de-DE")
    surfaces = resolution.surface_map()
    assert surfaces["browser_locale"] == "en-GB"
    assert surfaces["language_preference"] == "en"
    assert surfaces["http_language_preference"].startswith("en-GB")
    assert surfaces["javascript_locale_surface"] == "en-GB"
    assert surfaces["operating_system_locale"] == "de-DE"


def test_accept_language_quality_ordering():
    header = build_accept_language(["en-GB", "de-DE", "fr-FR"])
    assert header == "en-GB,de-DE;q=0.9,fr-FR;q=0.8"


def test_accept_language_wildcard_is_optional():
    assert build_accept_language(["en"], include_wildcard=True).endswith("*;q=0.1")


def test_browser_default_mode_follows_detected_locale():
    resolution = resolve(LocaleConfig(mode=LocaleMode.BROWSER_DEFAULT), "fr-FR")
    assert resolution.browser_locale == "fr-FR"
    assert resolution.source == "browser-default"


def test_manual_mode_requires_locale():
    try:
        resolve(LocaleConfig(mode=LocaleMode.MANUAL), None)
    except Exception as error:
        assert "manual locale mode requires a locale tag" in str(error)
    else:
        raise AssertionError("manual mode without locale must raise")


def test_language_entries_are_capped():
    header = build_accept_language([f"l{index}" for index in range(1, 20)])
    assert header.count(",") == 11
