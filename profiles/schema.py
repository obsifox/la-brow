"""Profile schema definition and validation."""

from __future__ import annotations

import math

from geo.models import GeoMode, RandomizationScope, validate_coordinate, validate_radius
from locale_engine.bcp47 import InvalidLanguageTagError, is_valid as is_valid_language
from profiles.errors import ProfileValidationError, ProfileVersionError
from timezone.engine import is_valid_zone
from webrtc.policy import WebRtcPolicy

CURRENT_PROFILE_VERSION = 2
SUPPORTED_PROFILE_VERSIONS = (1, 2)
NAME_MAX_LENGTH = 64
COUNTRY_CODE_LENGTH = 2

FIELD_TYPES = {
    "name": str,
    "profile_version": int,
    "country": str,
    "region": str,
    "city": str,
    "latitude": float,
    "longitude": float,
    "radius": float,
    "accuracy_m": float,
    "timezone": str,
    "locale": str,
    "languages": list,
    "dns": str,
    "doh": str,
    "dot": str,
    "webrtc_policy": str,
    "geolocation_mode": str,
    "randomization": str,
    "randomization_seed": int,
    "block_physical_fallback": bool,
    "conflict_detection": bool,
    "notes": str,
}

REQUIRED_FIELDS = ("name", "profile_version")


def unknown_fields(profile: dict) -> list[str]:
    return sorted(key for key in profile if key not in FIELD_TYPES)


def validate(profile: dict, allow_unknown: bool = False) -> dict:
    if not isinstance(profile, dict):
        raise ProfileValidationError("profile must be a mapping")
    problems: list[dict] = []
    for field in REQUIRED_FIELDS:
        if field not in profile:
            problems.append({"field": field, "issue": "required-field-missing"})
    version = profile.get("profile_version")
    if version is not None:
        if not isinstance(version, int) or isinstance(version, bool):
            problems.append({"field": "profile_version", "issue": "must-be-integer"})
        elif version not in SUPPORTED_PROFILE_VERSIONS:
            raise ProfileVersionError("unsupported profile version", version=version, supported=list(SUPPORTED_PROFILE_VERSIONS))
    name = profile.get("name")
    if name is not None:
        if not isinstance(name, str) or not name.strip():
            problems.append({"field": "name", "issue": "must-be-non-empty-string"})
        elif len(name) > NAME_MAX_LENGTH:
            problems.append({"field": "name", "issue": "too-long", "maximum": NAME_MAX_LENGTH})
    country = profile.get("country")
    if country is not None:
        if not isinstance(country, str) or len(country) != COUNTRY_CODE_LENGTH or not country.isalpha():
            problems.append({"field": "country", "issue": "must-be-iso-3166-alpha-2"})
    latitude = profile.get("latitude")
    longitude = profile.get("longitude")
    if (latitude is None) != (longitude is None):
        problems.append({"field": "latitude/longitude", "issue": "must-be-provided-together"})
    if latitude is not None and longitude is not None:
        try:
            validate_coordinate(latitude, longitude)
        except Exception as error:
            problems.append({"field": "latitude/longitude", "issue": str(error)})
    if profile.get("radius") is not None:
        try:
            validate_radius(profile["radius"])
        except Exception as error:
            problems.append({"field": "radius", "issue": str(error)})
    if profile.get("accuracy_m") is not None:
        accuracy = profile["accuracy_m"]
        if not isinstance(accuracy, (int, float)) or isinstance(accuracy, bool) or math.isnan(accuracy):
            problems.append({"field": "accuracy_m", "issue": "must-be-numeric"})
        elif accuracy <= 0:
            problems.append({"field": "accuracy_m", "issue": "must-be-positive"})
    if profile.get("timezone") is not None and not is_valid_zone(str(profile["timezone"])):
        problems.append({"field": "timezone", "issue": "unknown-iana-zone"})
    if profile.get("locale") is not None and not is_valid_language(str(profile["locale"])):
        problems.append({"field": "locale", "issue": "invalid-bcp47-tag"})
    languages = profile.get("languages")
    if languages is not None:
        if not isinstance(languages, list):
            problems.append({"field": "languages", "issue": "must-be-list"})
        else:
            for index, tag in enumerate(languages):
                if not isinstance(tag, str) or not is_valid_language(tag):
                    problems.append({"field": f"languages[{index}]", "issue": "invalid-bcp47-tag"})
    if profile.get("geolocation_mode") is not None:
        try:
            GeoMode(profile["geolocation_mode"])
        except ValueError:
            problems.append({"field": "geolocation_mode", "issue": "unsupported-mode", "allowed": [mode.value for mode in GeoMode]})
    randomization = profile.get("randomization")
    if randomization is not None and isinstance(randomization, str):
        try:
            RandomizationScope(randomization)
        except ValueError:
            problems.append({"field": "randomization", "issue": "unsupported-scope", "allowed": [scope.value for scope in RandomizationScope]})
    elif randomization is not None and isinstance(randomization, bool):
        problems.append({"field": "randomization", "issue": "boolean-form-is-not-supported-in-version-2"})
    if profile.get("webrtc_policy") is not None:
        try:
            WebRtcPolicy(profile["webrtc_policy"])
        except ValueError:
            problems.append({"field": "webrtc_policy", "issue": "unsupported-policy", "allowed": [policy.value for policy in WebRtcPolicy]})
    seed = profile.get("randomization_seed")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool) or seed < 0):
        problems.append({"field": "randomization_seed", "issue": "must-be-non-negative-integer"})
    for field, expected in FIELD_TYPES.items():
        if field in profile and field not in {"latitude", "longitude", "radius", "accuracy_m", "randomization", "randomization_seed"}:
            if expected is str and not isinstance(profile[field], str):
                problems.append({"field": field, "issue": "wrong-type", "expected": expected.__name__})
            if expected is bool and not isinstance(profile[field], bool):
                problems.append({"field": field, "issue": "wrong-type", "expected": "boolean"})
            if expected is int and field != "profile_version" and not isinstance(profile[field], int):
                if field == "randomization_seed":
                    continue
    if not allow_unknown:
        extra = unknown_fields(profile)
        if extra:
            problems.append({"field": "unknown", "issue": "unknown-fields-rejected", "fields": extra})
    if problems:
        raise ProfileValidationError("profile failed validation", problems=problems)
    return profile


def normalize(profile: dict) -> dict:
    result = dict(profile)
    result.setdefault("profile_version", CURRENT_PROFILE_VERSION)
    result.setdefault("geolocation_mode", GeoMode.MANUAL.value)
    result.setdefault("randomization", RandomizationScope.NONE.value)
    result.setdefault("block_physical_fallback", True)
    result.setdefault("conflict_detection", True)
    result.setdefault("webrtc_policy", WebRtcPolicy.DEFAULT.value)
    if "country" in result and isinstance(result["country"], str):
        result["country"] = result["country"].upper()
    if "languages" in result and isinstance(result["languages"], list):
        ordered: list[str] = []
        for tag in result["languages"]:
            if is_valid_language(tag) and tag not in ordered:
                ordered.append(tag)
        result["languages"] = ordered
    return result
