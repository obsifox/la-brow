"""WebExtension manifest parsing shared by the compatibility engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAMES = ("manifest.json",)
KNOWN_TYPES = ("extension", "theme", "locale", "dictionary")
SECTION_KEYS = (
    "manifest_version",
    "permissions",
    "optional_permissions",
    "host_permissions",
    "theme",
    "browser_action",
    "action",
    "browser_specific_settings",
    "content_scripts",
    "background",
    "options_ui",
    "commands",
    "sidebar_action",
    "chrome_url_overrides",
    "devtools_page",
    "userChrome",
    "experiment_apis",
)
SECTION_ALIASES = {
    "action": "browser_action",
}


class ManifestError(Exception):
    """Raised when a manifest cannot be read or does not satisfy the required fields."""

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.code = "manifest_invalid"
        self.message = message
        self.context = dict(context)

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


@dataclass
class WebExtensionManifest:
    name: str
    version: str
    manifest_version: int
    type: str
    description: str
    permissions: list[str]
    optional_permissions: list[str]
    host_permissions: list[str]
    raw: dict
    theme: dict
    background: dict
    content_scripts: list
    declared_sections: list[str]

    def declared_permissions(self) -> list[str]:
        seen: list[str] = []
        for value in [*self.permissions, *self.optional_permissions, *self.host_permissions]:
            if value not in seen:
                seen.append(value)
        return seen

    def as_record(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "manifest_version": self.manifest_version,
            "type": self.type,
            "description": self.description,
            "permissions": self.declared_permissions(),
            "sections": list(self.declared_sections),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.raw, sort_keys=True, separators=(",", ":"))


def read_manifest_file(path: Path) -> dict:
    if not path.is_file():
        raise ManifestError("manifest file not found", path=str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManifestError("manifest file is not valid json", detail=str(error)) from error
    if not isinstance(payload, dict):
        raise ManifestError("manifest root must be a json object")
    return payload


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(entry) for entry in value if isinstance(entry, (str, int, float))]
    return []


def parse_manifest(payload: dict) -> WebExtensionManifest:
    if not isinstance(payload, dict):
        raise ManifestError("manifest root must be a json object")
    manifest_version = payload.get("manifest_version")
    if manifest_version not in (2, 3):
        raise ManifestError("manifest_version must be 2 or 3", value=manifest_version)
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ManifestError("manifest name is required")
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ManifestError("manifest version is required")
    declared_type = payload.get("type", "extension")
    if not isinstance(declared_type, str) or declared_type not in KNOWN_TYPES:
        raise ManifestError("manifest type is not recognised", value=declared_type)
    theme = payload.get("theme") if isinstance(payload.get("theme"), dict) else {}
    if declared_type == "theme" and not theme:
        raise ManifestError("theme manifests must declare a theme section")
    background = payload.get("background") if isinstance(payload.get("background"), dict) else {}
    content_scripts = payload.get("content_scripts") if isinstance(payload.get("content_scripts"), list) else []
    sections = [key for key in SECTION_KEYS if key in payload]
    return WebExtensionManifest(
        name=name.strip(),
        version=version.strip(),
        manifest_version=int(manifest_version),
        type=declared_type,
        description=str(payload.get("description", "")),
        permissions=_string_list(payload.get("permissions")),
        optional_permissions=_string_list(payload.get("optional_permissions")),
        host_permissions=_string_list(payload.get("host_permissions")),
        raw=payload,
        theme=theme,
        background=background,
        content_scripts=content_scripts,
        declared_sections=sections,
    )
