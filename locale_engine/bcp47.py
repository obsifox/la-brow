"""Minimal BCP 47 language tag parsing and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}$")
SCRIPT_PATTERN = re.compile(r"^[A-Za-z]{4}$")
REGION_PATTERN = re.compile(r"^([A-Za-z]{2}|\d{3})$")
VARIANT_PATTERN = re.compile(r"^([A-Za-z0-9]{5,8}|\d[A-Za-z0-9]{3})$")
EXTENSION_PATTERN = re.compile(r"^[A-Za-z0-9]{1,8}$")
PRIVATE_USE_PATTERN = re.compile(r"^x(-[A-Za-z0-9]{1,8})+$")
GRANDFATHERED = {"i-default", "i-klingon", "en-GB-oed", "zh-min-nan"}
MAX_TAG_LENGTH = 63


class InvalidLanguageTagError(ValueError):
    code = "locale_invalid_tag"

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


@dataclass(frozen=True)
class LanguageTag:
    language: str
    script: str | None = None
    region: str | None = None
    variants: tuple[str, ...] = ()
    extlang: str | None = None

    def canonical(self) -> str:
        parts = [self.language.lower()]
        if self.extlang:
            parts.append(self.extlang.lower())
        if self.script:
            parts.append(self.script.title())
        if self.region:
            parts.append(self.region.upper())
        parts.extend(self.variants)
        return "-".join(parts)

    def as_dict(self) -> dict:
        return {
            "language": self.language.lower(),
            "script": None if self.script is None else self.script.title(),
            "region": None if self.region is None else self.region.upper(),
            "variants": list(self.variants),
            "extlang": self.extlang,
            "canonical": self.canonical(),
        }


def parse(tag: str) -> LanguageTag:
    if not isinstance(tag, str):
        raise InvalidLanguageTagError("language tag must be a string")
    candidate = tag.strip()
    if not candidate:
        raise InvalidLanguageTagError("language tag must not be empty")
    if len(candidate) > MAX_TAG_LENGTH:
        raise InvalidLanguageTagError("language tag exceeds maximum length", length=len(candidate))
    lowered = candidate.lower()
    if lowered in GRANDFATHERED:
        parts = candidate.split("-")
        return LanguageTag(language=parts[0], region=parts[1] if len(parts) > 1 else None, variants=tuple(parts[2:]))
    if PRIVATE_USE_PATTERN.match(candidate):
        parts = candidate.split("-")
        return LanguageTag(language=parts[0], variants=tuple(parts[1:]))
    parts = candidate.split("-")
    if not LANGUAGE_PATTERN.match(parts[0]):
        raise InvalidLanguageTagError("invalid primary language subtag", subtag=parts[0])
    language = parts[0]
    index = 1
    extlang = None
    script = None
    region = None
    variants: list[str] = []
    if index < len(parts) and LANGUAGE_PATTERN.match(parts[index]) and len(parts[index]) == 3:
        extlang = parts[index]
        index += 1
    if index < len(parts) and SCRIPT_PATTERN.match(parts[index]):
        script = parts[index]
        index += 1
    if index < len(parts) and REGION_PATTERN.match(parts[index]):
        region = parts[index]
        index += 1
    while index < len(parts) and VARIANT_PATTERN.match(parts[index]):
        variants.append(parts[index].lower())
        index += 1
    while index < len(parts):
        if parts[index] == "x":
            break
        if not EXTENSION_PATTERN.match(parts[index]):
            raise InvalidLanguageTagError("invalid extension subtag", subtag=parts[index])
        index += 1
    return LanguageTag(language=language, script=script, region=region, variants=tuple(variants), extlang=extlang)


def is_valid(tag: str) -> bool:
    try:
        parse(tag)
    except InvalidLanguageTagError:
        return False
    return True


def canonicalize(tag: str) -> str:
    return parse(tag).canonical()


def matches_region_free(tag: str, language: str) -> bool:
    return parse(tag).language.lower() == language.lower()
