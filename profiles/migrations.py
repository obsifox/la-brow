"""Deterministic profile version migrations."""

from __future__ import annotations

from geo.models import RandomizationScope
from profiles.errors import ProfileMigrationError
from profiles.schema import CURRENT_PROFILE_VERSION

MIGRATION_PATH = {1: 2}

BOOLEAN_RANDOMIZATION_MAP = {True: RandomizationScope.PER_SESSION.value, False: RandomizationScope.NONE.value}


def migrate_step_1_to_2(profile: dict) -> dict:
    migrated = dict(profile)
    randomization = migrated.get("randomization")
    if isinstance(randomization, bool):
        migrated["randomization"] = BOOLEAN_RANDOMIZATION_MAP[randomization]
    elif randomization is None:
        migrated["randomization"] = RandomizationScope.NONE.value
    dns_value = migrated.pop("dns_resolver", None)
    if dns_value is not None:
        migrated.setdefault("dns", dns_value)
    doh_value = migrated.pop("doh_enabled", None)
    if doh_value is not None:
        migrated.setdefault("doh", "enabled" if doh_value else "disabled")
    migrated["profile_version"] = 2
    migrated.setdefault("block_physical_fallback", True)
    return migrated


MIGRATIONS = {1: migrate_step_1_to_2}


def migrate(profile: dict) -> tuple[dict, list[dict]]:
    version = profile.get("profile_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProfileMigrationError("profile version must be an integer before migration", version=version)
    if version > CURRENT_PROFILE_VERSION:
        raise ProfileMigrationError(
            "profile version is newer than the supported version",
            version=version,
            supported=CURRENT_PROFILE_VERSION,
        )
    applied: list[dict] = []
    current = dict(profile)
    while current["profile_version"] < CURRENT_PROFILE_VERSION:
        source_version = current["profile_version"]
        step = MIGRATIONS.get(source_version)
        if step is None:
            raise ProfileMigrationError("no migration path available", from_version=source_version)
        current = step(current)
        applied.append(
            {
                "from_version": source_version,
                "to_version": current["profile_version"],
                "migration": f"migrate_step_{source_version}_to_{current['profile_version']}",
            }
        )
    return current, applied


def supported_migration_path() -> list[dict]:
    return [{"from_version": source, "to_version": target} for source, target in sorted(MIGRATION_PATH.items())]
