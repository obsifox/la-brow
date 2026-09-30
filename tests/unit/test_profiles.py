"""Profile schema, migration, integrity and store tests."""

from __future__ import annotations

import json

import pytest

from profiles.errors import ProfileIntegrityError, ProfileMigrationError, ProfileStoreError, ProfileValidationError, ProfileVersionError
from profiles.integrity import checksum, envelope, open_envelope, sign, verify_checksum
from profiles.migrations import migrate, supported_migration_path
from profiles.schema import CURRENT_PROFILE_VERSION, normalize, validate
from profiles.store import ProfileStore


def test_current_version_is_two():
    assert CURRENT_PROFILE_VERSION == 2
    assert supported_migration_path() == [{"from_version": 1, "to_version": 2}]


def test_valid_profile_passes(profile_payload):
    validate(normalize(profile_payload))


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude", 95.0),
        ("longitude", -700.0),
        ("radius", -5),
        ("timezone", "Mars/Olympus"),
        ("locale", "not_a_locale"),
        ("geolocation_mode", "teleport"),
        ("webrtc_policy", "invisible"),
        ("country", "Germany"),
    ],
)
def test_invalid_field_values_are_rejected(profile_payload, field, value):
    payload = dict(profile_payload)
    payload[field] = value
    with pytest.raises(ProfileValidationError):
        validate(normalize(payload))


def test_unknown_fields_are_rejected_by_default(profile_payload):
    payload = dict(profile_payload, mystery_field=1)
    with pytest.raises(ProfileValidationError):
        validate(payload)


def test_unknown_fields_can_be_allowed_for_forward_compatibility(profile_payload):
    payload = dict(profile_payload, future_field="value")
    validate(payload, allow_unknown=True)


def test_newer_profile_version_is_rejected(profile_payload):
    payload = dict(profile_payload, profile_version=99)
    with pytest.raises(ProfileVersionError):
        validate(payload)


def test_latitude_without_longitude_is_rejected(profile_payload):
    payload = dict(profile_payload)
    payload.pop("longitude")
    with pytest.raises(ProfileValidationError):
        validate(payload)


def test_migration_from_version_one():
    legacy = {
        "name": "legacy",
        "profile_version": 1,
        "randomization": True,
        "dns_resolver": "cloudflare-doh",
        "doh_enabled": True,
        "country": "NL",
        "latitude": 52.37,
        "longitude": 4.89,
    }
    migrated, applied = migrate(legacy)
    assert migrated["profile_version"] == 2
    assert migrated["randomization"] == "per_session"
    assert migrated["dns"] == "cloudflare-doh"
    assert migrated["doh"] == "enabled"
    assert applied[0]["migration"] == "migrate_step_1_to_2"


def test_boolean_randomization_in_version_two_is_rejected(profile_payload):
    payload = dict(profile_payload, randomization=True)
    with pytest.raises(ProfileValidationError):
        validate(payload)


def test_migration_rejects_unsupported_version():
    with pytest.raises(ProfileMigrationError):
        migrate({"name": "x", "profile_version": 99})


def test_checksum_and_signature_round_trip(profile_payload):
    profile = normalize(profile_payload)
    assert verify_checksum(profile, checksum(profile)) is None
    key = b"unit-test-key"
    package = envelope(profile, key)
    assert package["integrity"]["signed"] is True
    assert open_envelope(package, key)["name"] == profile["name"]
    assert sign(profile, key) == package["integrity"]["signature"]


def test_tampered_profile_fails_integrity_check(profile_payload):
    profile = normalize(profile_payload)
    package = envelope(profile, b"key")
    package["profile"]["latitude"] = 10.0
    with pytest.raises(ProfileIntegrityError):
        open_envelope(package, b"key")


def test_unsigned_profile_is_rejected_when_signature_is_required(profile_payload):
    package = envelope(normalize(profile_payload))
    with pytest.raises(ProfileIntegrityError):
        open_envelope(package, None, require_signature=True)


def test_store_round_trip(tmp_path, profile_payload):
    store = ProfileStore(tmp_path)
    saved = store.save(profile_payload, "berlin")
    assert saved["profile_version"] == 2
    loaded = store.load("berlin")
    assert loaded["city"] == "Berlin"
    assert store.list_profiles()[0]["id"] == "berlin"
    assert json.loads(store.export("berlin"))["profile"]["name"] == profile_payload["name"]


def test_store_rejects_traversal_identifiers(tmp_path, profile_payload):
    store = ProfileStore(tmp_path)
    for candidate in ("../escape", "/etc/passwd", "bad id", "..", "A-Upper"):
        with pytest.raises(ProfileStoreError):
            store.save(profile_payload, candidate)


def test_store_import_validates_and_migrates(tmp_path):
    store = ProfileStore(tmp_path)
    legacy = json.dumps({"name": "legacy", "profile_version": 1, "randomization": False, "country": "NL", "radius": 0})
    result = store.import_payload(legacy, "legacy-profile")
    assert result["activated"] is True
    assert result["migrations_applied"][0]["to_version"] == 2
    assert store.load("legacy-profile")["randomization"] == "none"


def test_store_import_dry_run_does_not_persist(tmp_path, profile_payload):
    store = ProfileStore(tmp_path)
    result = store.import_payload(json.dumps(profile_payload), "dry", dry_run=True)
    assert result["activated"] is False
    assert store.list_profiles() == []


def test_store_import_rejects_oversized_payload(tmp_path):
    store = ProfileStore(tmp_path)
    with pytest.raises(ProfileStoreError):
        store.import_payload("{" + "a" * 300000 + "}")


def test_store_import_rejects_invalid_json(tmp_path):
    store = ProfileStore(tmp_path)
    with pytest.raises(ProfileStoreError):
        store.import_payload("not-json")


def test_store_rollback_restores_previous_revision(tmp_path, profile_payload):
    store = ProfileStore(tmp_path)
    store.save(profile_payload, "berlin")
    updated = dict(profile_payload, city="Hamburg", latitude=53.55, longitude=9.99)
    store.save(updated, "berlin")
    assert store.load("berlin")["city"] == "Hamburg"
    result = store.rollback("berlin")
    assert result["id"] == "berlin"
    assert store.load("berlin")["city"] == "Berlin"


def test_store_rollback_without_backup_fails(tmp_path, profile_payload):
    store = ProfileStore(tmp_path)
    store.save(profile_payload, "berlin")
    with pytest.raises(ProfileStoreError):
        store.rollback("berlin")
