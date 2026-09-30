"""Browser scoped locale and language preference resolution."""

from __future__ import annotations

import os

from locale_engine.bcp47 import InvalidLanguageTagError, canonicalize, parse
from locale_engine.models import LocaleConfig, LocaleMode, LocaleResolution

DEFAULT_FALLBACK = "en-US"
MAX_LANGUAGE_ENTRIES = 12
QUALITY_STEP_PERCENT = 10


def system_locale_names() -> list[str]:
    names: list[str] = []
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(variable)
        if not value:
            continue
        for entry in value.split(":"):
            cleaned = entry.split(".")[0].strip()
            if cleaned and cleaned not in names:
                names.append(cleaned)
    return names


def default_locale() -> str:
    for candidate in system_locale_names():
        normalized = candidate.replace("_", "-")
        try:
            return canonicalize(normalized)
        except InvalidLanguageTagError:
            continue
    return DEFAULT_FALLBACK


def build_accept_language(languages: list[str], include_wildcard: bool = False) -> str:
    entries: list[str] = []
    for index, tag in enumerate(languages[:MAX_LANGUAGE_ENTRIES]):
        quality = max(100 - index * QUALITY_STEP_PERCENT, 10)
        if quality == 100 and index == 0:
            entries.append(tag)
        else:
            entries.append(f"{tag};q={quality / 100:.1f}")
    if include_wildcard:
        entries.append("*;q=0.1")
    return ",".join(entries)


def resolve(config: LocaleConfig, detected_locale: str | None) -> LocaleResolution:
    notes: list[str] = []
    os_locale = detected_locale or default_locale()
    if config.mode is LocaleMode.DISABLED:
        browser_locale = os_locale
        source = "operating-system"
        confidence = 0.5
        notes.append("locale control is disabled; browser surfaces follow the operating system locale")
    elif config.mode is LocaleMode.MANUAL:
        if not config.locale:
            raise InvalidLanguageTagError("manual locale mode requires a locale tag")
        browser_locale = canonicalize(config.locale)
        source = "manual-configuration"
        confidence = 1.0
    elif config.mode is LocaleMode.PROFILE:
        if not config.locale:
            raise InvalidLanguageTagError("profile locale mode requires a locale tag")
        browser_locale = canonicalize(config.locale)
        source = f"profile:{config.source_profile or 'unnamed'}"
        confidence = 0.95
    else:
        browser_locale = canonicalize(os_locale)
        source = "browser-default"
        confidence = 0.8
        notes.append("browser default mode follows the detected system locale")
    languages = [canonicalize(tag) for tag in config.languages]
    if browser_locale not in languages:
        languages.insert(0, browser_locale)
    primary_language = parse(browser_locale).language
    http_preference = build_accept_language(languages)
    notes.append("browser locale, language preference, HTTP preference, JavaScript surface and operating system locale are distinct values")
    if parse(browser_locale).region is None:
        notes.append("browser locale has no region subtag; region dependent formatting will use the primary language default")
    return LocaleResolution(
        mode=config.mode,
        browser_locale=browser_locale,
        language_preference=primary_language,
        http_language_preference=http_preference,
        javascript_locale_surface=browser_locale,
        operating_system_locale=os_locale,
        accepted_languages=languages,
        confidence=confidence,
        source=source,
        notes=notes,
    )
