"""Application settings persistence."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone as timezone_module
from pathlib import Path

DEFAULT_SETTINGS = {
    "schema_version": 1,
    "default_url": "https://example.com/",
    "active_profile": "default",
    "resolver_profile": "system",
    "privacy_preset": "balanced",
    "diagnostics_level": "redacted",
    "private_browsing": False,
    "consistency_on_load": True,
}


def utc_stamp() -> str:
    return datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SettingsStore:
    """Reads and writes the application settings document."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "settings.json"

    def load(self) -> dict:
        if not self.path.is_file():
            self.save(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return dict(DEFAULT_SETTINGS)
        merged = dict(DEFAULT_SETTINGS)
        merged.update({key: value for key, value in payload.items() if key in DEFAULT_SETTINGS})
        merged["schema_version"] = DEFAULT_SETTINGS["schema_version"]
        return merged

    def save(self, settings: dict) -> dict:
        merged = dict(DEFAULT_SETTINGS)
        merged.update({key: value for key, value in settings.items() if key in DEFAULT_SETTINGS})
        document = dict(merged)
        document["updated_at"] = utc_stamp()
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        return merged
