"""Value objects for the locale subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LocaleMode(str, Enum):
    BROWSER_DEFAULT = "browser_default"
    MANUAL = "manual"
    PROFILE = "profile"
    DISABLED = "disabled"


class LocaleSurface(str, Enum):
    BROWSER_LOCALE = "browser_locale"
    LANGUAGE_PREFERENCE = "language_preference"
    HTTP_LANGUAGE_PREFERENCE = "http_language_preference"
    JAVASCRIPT_LOCALE_SURFACE = "javascript_locale_surface"
    OPERATING_SYSTEM_LOCALE = "operating_system_locale"


@dataclass(frozen=True)
class LocaleConfig:
    mode: LocaleMode
    locale: str | None = None
    languages: tuple[str, ...] = ()
    source_profile: str | None = None


@dataclass
class LocaleResolution:
    mode: LocaleMode
    browser_locale: str
    language_preference: str
    http_language_preference: str
    javascript_locale_surface: str
    operating_system_locale: str
    accepted_languages: list[str] = field(default_factory=list)
    confidence: float = 0.9
    source: str = "browser-default"
    notes: list[str] = field(default_factory=list)

    def surface_map(self) -> dict:
        return {
            "browser_locale": self.browser_locale,
            "language_preference": self.language_preference,
            "http_language_preference": self.http_language_preference,
            "javascript_locale_surface": self.javascript_locale_surface,
            "operating_system_locale": self.operating_system_locale,
        }

    def as_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "surfaces": self.surface_map(),
            "accepted_languages": list(self.accepted_languages),
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "notes": list(self.notes),
        }
