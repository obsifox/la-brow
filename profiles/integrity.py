"""Profile payload canonicalization and integrity metadata."""

from __future__ import annotations

import hashlib
import hmac
import json

from profiles.errors import ProfileIntegrityError

CHECKSUM_ALGORITHM = "sha256"


def canonical_bytes(profile: dict) -> bytes:
    return json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def checksum(profile: dict) -> str:
    return hashlib.sha256(canonical_bytes(profile)).hexdigest()


def sign(profile: dict, key: bytes) -> str:
    return hmac.new(key, canonical_bytes(profile), hashlib.sha256).hexdigest()


def verify_checksum(profile: dict, expected: str) -> None:
    actual = checksum(profile)
    if not hmac.compare_digest(actual, expected):
        raise ProfileIntegrityError("profile checksum mismatch", expected=expected, actual=actual)


def verify_signature(profile: dict, signature: str, key: bytes) -> None:
    expected = sign(profile, key)
    if not hmac.compare_digest(expected, signature):
        raise ProfileIntegrityError("profile signature mismatch")


def envelope(profile: dict, key: bytes | None = None) -> dict:
    result = {
        "integrity": {
            "algorithm": CHECKSUM_ALGORITHM,
            "checksum": checksum(profile),
            "signed": key is not None,
            "signature": None if key is None else sign(profile, key),
        },
        "profile": profile,
    }
    return result


def open_envelope(payload: dict, key: bytes | None = None, require_signature: bool = False) -> dict:
    if not isinstance(payload, dict) or "profile" not in payload or "integrity" not in payload:
        raise ProfileIntegrityError("profile envelope is malformed")
    integrity = payload["integrity"]
    profile = payload["profile"]
    verify_checksum(profile, integrity.get("checksum", ""))
    if integrity.get("signed"):
        if key is None:
            raise ProfileIntegrityError("signed profile requires a verification key")
        verify_signature(profile, integrity.get("signature", ""), key)
    elif require_signature:
        raise ProfileIntegrityError("unsigned profile rejected by policy")
    return profile
