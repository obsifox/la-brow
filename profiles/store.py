"""Profile storage with versioning, integrity and safe import and export."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone as timezone_module
from pathlib import Path

from profiles.errors import ProfileError, ProfileIntegrityError, ProfileStoreError, ProfileValidationError
from profiles.integrity import envelope, open_envelope
from profiles.migrations import migrate, supported_migration_path
from profiles.schema import CURRENT_PROFILE_VERSION, normalize, validate

PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
IMPORT_MAX_BYTES = 262144
INDEX_NAME = "index.json"
PROFILES_DIRECTORY = "profiles"
BACKUP_DIRECTORY = "backups"


def validate_profile_id(profile_id: str) -> str:
    if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.match(profile_id):
        raise ProfileStoreError("invalid profile identifier", profile_id=profile_id)
    if ".." in profile_id or profile_id.startswith("/"):
        raise ProfileStoreError("profile identifier must not contain traversal sequences", profile_id=profile_id)
    return profile_id


def utc_stamp() -> str:
    return datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ProfileStore:
    """Persists profiles in an explicit directory layout."""

    def __init__(self, root: Path, key: bytes | None = None) -> None:
        self.root = Path(root)
        self.profiles_dir = self.root / PROFILES_DIRECTORY
        self.backup_dir = self.profiles_dir / BACKUP_DIRECTORY
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.key = key

    def index_path(self) -> Path:
        return self.profiles_dir / INDEX_NAME

    def path_for(self, profile_id: str) -> Path:
        return self.profiles_dir / f"{validate_profile_id(profile_id)}.json"

    def read_index(self) -> dict:
        if not self.index_path().is_file():
            return {"schema_version": 1, "profiles": []}
        return json.loads(self.index_path().read_text(encoding="utf-8"))

    def write_index(self) -> dict:
        entries = []
        for path in sorted(self.profiles_dir.glob("*.json")):
            if path.name == INDEX_NAME:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            profile = payload.get("profile", payload)
            entries.append(
                {
                    "id": path.stem,
                    "name": profile.get("name"),
                    "profile_version": profile.get("profile_version"),
                    "updated_at": payload.get("updated_at", utc_stamp()),
                }
            )
        index = {"schema_version": 1, "profile_version_current": CURRENT_PROFILE_VERSION, "profiles": entries}
        self._atomic_write(self.index_path(), json.dumps(index, indent=2, sort_keys=True) + "\n")
        return index

    def save(self, profile: dict, profile_id: str | None = None, allow_unknown: bool = False) -> dict:
        normalized = normalize(profile)
        validate(normalized, allow_unknown=allow_unknown)
        target_id = validate_profile_id(profile_id or str(normalized["name"]).lower().replace(" ", "-"))
        payload = {
            "updated_at": utc_stamp(),
            "integrity": {"algorithm": "sha256", "checksum": None},
            "profile": normalized,
        }
        payload["integrity"]["checksum"] = envelope(normalized, self.key)["integrity"]["checksum"]
        if self.key is not None:
            payload["integrity"]["signed"] = True
            payload["integrity"]["signature"] = envelope(normalized, self.key)["integrity"]["signature"]
        existing = self.path_for(target_id)
        if existing.is_file():
            self._backup(target_id)
        self._atomic_write(existing, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self.write_index()
        return {"id": target_id, "path": str(existing), "profile_version": normalized["profile_version"]}

    def load(self, profile_id: str, require_signature: bool = False) -> dict:
        path = self.path_for(profile_id)
        if not path.is_file():
            raise ProfileStoreError("profile not found", profile_id=profile_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "integrity" in payload:
            profile = open_envelope(payload, self.key, require_signature=require_signature)
        else:
            profile = payload
        validate(profile, allow_unknown=True)
        return profile

    def delete(self, profile_id: str) -> dict:
        path = self.path_for(profile_id)
        if not path.is_file():
            raise ProfileStoreError("profile not found", profile_id=profile_id)
        self._backup(profile_id)
        path.unlink()
        self.write_index()
        return {"id": profile_id, "deleted": True}

    def list_profiles(self) -> list[dict]:
        return self.read_index().get("profiles", [])

    def export(self, profile_id: str) -> str:
        profile = self.load(profile_id, require_signature=False)
        payload = envelope(profile, self.key)
        payload["exported_at"] = utc_stamp()
        payload["migration_path"] = supported_migration_path()
        return json.dumps(payload, indent=2, sort_keys=True)

    def import_payload(self, raw: str, profile_id: str | None = None, require_signature: bool = False, dry_run: bool = False) -> dict:
        if len(raw.encode("utf-8")) > IMPORT_MAX_BYTES:
            raise ProfileStoreError("import payload exceeds maximum size", maximum_bytes=IMPORT_MAX_BYTES)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProfileStoreError("import payload is not valid json", detail=str(error)) from error
        profile = payload.get("profile", payload) if isinstance(payload, dict) else None
        if not isinstance(profile, dict):
            raise ProfileValidationError("import payload does not contain a profile mapping")
        if isinstance(payload, dict) and "integrity" in payload:
            profile = open_envelope(payload, self.key, require_signature=require_signature)
        migrated, applied = migrate(profile)
        normalized = normalize(migrated)
        validate(normalized, allow_unknown=False)
        result = {
            "profile": normalized,
            "migrations_applied": applied,
            "dry_run": dry_run,
            "activated": False,
            "notes": ["imported profiles are treated as untrusted input and validated before activation"],
        }
        if dry_run:
            return result
        saved = self.save(normalized, profile_id)
        result.update({"activated": True, "id": saved["id"], "path": saved["path"]})
        return result

    def rollback(self, profile_id: str) -> dict:
        validate_profile_id(profile_id)
        backups = sorted(self.backup_dir.glob(f"{profile_id}.*.json"))
        if not backups:
            raise ProfileStoreError("no backup available for rollback", profile_id=profile_id)
        latest = backups[-1]
        payload = json.loads(latest.read_text(encoding="utf-8"))
        profile = payload.get("profile", payload)
        validate(profile, allow_unknown=True)
        self._atomic_write(self.path_for(profile_id), json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self.write_index()
        return {"id": profile_id, "restored_from": str(latest), "profile_version": profile.get("profile_version")}

    def _backup(self, profile_id: str) -> Path:
        source = self.path_for(profile_id)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        target = self.backup_dir / f"{profile_id}.{stamp}.json"
        self._atomic_write(target, source.read_text(encoding="utf-8"))
        return target

    def _atomic_write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
