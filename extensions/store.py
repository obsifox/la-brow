"""Installed extension and theme registry."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone as timezone_module
from pathlib import Path

from extensions.compat import CompatibilityEngine
from extensions.manifest import ManifestError, parse_manifest
from extensions.policy import evaluate_install, signature_state
from extensions.themes import ThemeSpecError, slugify, theme_spec

INDEX_NAME = "index.json"
INDEX_VERSION = 1
IDENTIFIER_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def utc_stamp() -> str:
    return datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def valid_identifier(value: str) -> bool:
    if not value or len(value) > 63:
        return False
    if not value[0].isalnum():
        return False
    return all(character in IDENTIFIER_CHARS for character in value)


class ExtensionStoreError(Exception):
    def __init__(self, message: str, code: str = "extension_store_error", **context: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = dict(context)

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


class ExtensionStore:
    """Registry of inspected and installed add-ons stored under the repository variable tree."""

    def __init__(self, repo: Path, root: Path | None = None) -> None:
        self.repo = Path(repo)
        self.root = Path(root) if root is not None else self.repo / "var/extensions"
        self.path = self.root / INDEX_NAME
        self.engine = CompatibilityEngine(repo)
        self.signature = signature_state(repo)

    def load(self) -> dict:
        if not self.path.is_file():
            return {"schema_version": INDEX_VERSION, "extensions": [], "active_theme": None}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("schema_version", INDEX_VERSION)
        payload.setdefault("extensions", [])
        payload.setdefault("active_theme", None)
        return payload

    def _write(self, payload: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def _entry(self, identifier: str) -> dict:
        for entry in self.load()["extensions"]:
            if entry["id"] == identifier:
                return entry
        raise ExtensionStoreError("extension not found", identifier=identifier)

    def inspect(self, payload: dict) -> dict:
        manifest = parse_manifest(payload)
        compatibility = self.engine.evaluate(manifest)
        theme = None
        if manifest.type == "theme":
            try:
                theme = theme_spec(manifest, compatibility["level"])
            except ThemeSpecError as error:
                theme = {"error": error.as_dict()}
        decision = evaluate_install(self.repo, payload, acknowledged=False)
        return {
            "manifest": manifest.as_record(),
            "compatibility": compatibility,
            "theme": theme,
            "install_preview": decision,
            "notice": self.engine.notice(),
        }

    def install(self, payload: dict, identifier: str | None = None, acknowledged: bool = False) -> dict:
        manifest = parse_manifest(payload)
        decision = evaluate_install(self.repo, payload, acknowledged=acknowledged)
        if not decision["allowed"]:
            raise ExtensionStoreError(decision["message"], code=decision["code"], **decision.get("context", {}))
        compatibility = self.engine.evaluate(manifest)
        theme = None
        if manifest.type == "theme":
            theme = theme_spec(manifest, compatibility["level"])
        digest = hashlib.sha256(manifest.canonical_json().encode("utf-8")).hexdigest()
        if identifier:
            target_id = identifier
        elif theme is not None:
            target_id = theme["id"]
        else:
            target_id = slugify(f"{manifest.name}-{manifest.version}")
        if not valid_identifier(target_id):
            raise ExtensionStoreError("identifier is not valid", identifier=target_id)
        record = {
            "id": target_id,
            "name": manifest.name,
            "version": manifest.version,
            "type": manifest.type,
            "description": manifest.description,
            "manifest_version": manifest.manifest_version,
            "manifest_sha256": digest,
            "compatibility_level": compatibility["level"],
            "compatibility_score": compatibility["score"],
            "compatibility_findings": compatibility["findings"],
            "installed_at": utc_stamp(),
            "notice_acknowledged": True,
            "notice_text": self.engine.notice(),
            "signature": self.signature,
            "theme": theme,
            "manifest": manifest.raw,
        }
        index = self.load()
        index["extensions"] = [entry for entry in index["extensions"] if entry["id"] != target_id]
        index["extensions"].append(record)
        if theme is not None and index.get("active_theme") is None:
            index["active_theme"] = target_id
        self._write(index)
        return record

    def remove(self, identifier: str) -> dict:
        index = self.load()
        entry = self._entry(identifier)
        index["extensions"] = [item for item in index["extensions"] if item["id"] != identifier]
        if index.get("active_theme") == identifier:
            remaining = [item for item in index["extensions"] if item.get("theme")]
            index["active_theme"] = remaining[0]["id"] if remaining else None
        self._write(index)
        return {"id": identifier, "removed": True, "was_type": entry["type"]}

    def list_records(self) -> dict:
        index = self.load()
        return {
            "extensions": index["extensions"],
            "themes": [entry for entry in index["extensions"] if entry.get("theme")],
            "active_theme": index.get("active_theme"),
            "notice": self.engine.notice(),
            "signature_state": self.signature,
            "count": len(index["extensions"]),
        }

    def active_theme_spec(self) -> dict:
        index = self.load()
        identifier = index.get("active_theme")
        if identifier is None:
            return {
                "id": "product-default",
                "name": "Product default",
                "source": "product-default",
                "palette": None,
                "gradient": None,
                "properties": {"color_scheme": "dark", "content_color_scheme": "dark"},
                "findings": [],
            }
        entry = self._entry(identifier)
        return entry.get("theme") or {"id": identifier, "source": "not-a-theme", "gradient": None}

    def activate_theme(self, identifier: str) -> dict:
        index = self.load()
        entry = self._entry(identifier)
        if not entry.get("theme"):
            raise ExtensionStoreError("the selected add-on does not provide a theme", identifier=identifier)
        index["active_theme"] = identifier
        self._write(index)
        return {"active_theme": identifier, "theme": entry["theme"]}
