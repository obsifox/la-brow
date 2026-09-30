"""Redaction levels for diagnostic export."""

from __future__ import annotations

from enum import Enum

IP_KEYS = ("ip", "ip_address", "address", "resolver_addresses", "bootstrap_addresses", "remote_address")
HOST_KEYS = ("hostname", "host", "endpoint")
COORDINATE_KEYS = ("latitude", "longitude")
TOKEN_KEYS = ("token", "secret", "password", "credential", "authorization", "api_key")


class RedactionLevel(str, Enum):
    FULL = "full"
    REDACTED = "redacted"
    MINIMAL = "minimal"


DEFAULT_LEVEL = RedactionLevel.REDACTED


def redact_ip(value: str) -> str:
    if ":" in value:
        blocks = value.split(":")
        return ":".join(blocks[:2] + ["xxxx"] * max(0, len(blocks) - 2))
    blocks = value.split(".")
    if len(blocks) == 4:
        return ".".join(blocks[:2] + ["x", "x"])
    return "[redacted]"


def _walk(node, level: RedactionLevel):
    if isinstance(node, dict):
        result = {}
        for key, value in node.items():
            lowered = key.lower()
            if any(fragment in lowered for fragment in TOKEN_KEYS):
                result[key] = "[removed]"
                continue
            if level is not RedactionLevel.FULL and any(fragment in lowered for fragment in IP_KEYS) and isinstance(value, (str, list)):
                if isinstance(value, list):
                    result[key] = [redact_ip(str(item)) for item in value]
                else:
                    result[key] = redact_ip(value)
                continue
            if level is RedactionLevel.MINIMAL and any(fragment in lowered for fragment in COORDINATE_KEYS) and isinstance(value, (int, float)):
                result[key] = "[removed]"
                continue
            if level is RedactionLevel.REDACTED and any(fragment == lowered for fragment in COORDINATE_KEYS) and isinstance(value, (int, float)):
                result[key] = round(float(value), 1)
                continue
            if level is RedactionLevel.MINIMAL and any(fragment in lowered for fragment in HOST_KEYS) and isinstance(value, str):
                result[key] = "[removed]"
                continue
            result[key] = _walk(value, level)
        return result
    if isinstance(node, list):
        return [_walk(item, level) for item in node]
    return node


def redact(document: dict, level: RedactionLevel = DEFAULT_LEVEL) -> dict:
    result = _walk(document, level)
    result["redaction"] = {
        "level": level.value,
        "default_level": DEFAULT_LEVEL.value,
        "notes": [
            "coordinates are rounded at redacted level and removed at minimal level",
            "ip addresses are masked unless the full level is explicitly requested",
            "authentication tokens are never exported",
        ],
    }
    return result
