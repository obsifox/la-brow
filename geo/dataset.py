"""Read only access to the bundled country dataset."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATASET_PATH = Path(__file__).parent / "data" / "country-centroids.json"


@lru_cache(maxsize=1)
def load_countries() -> dict:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return payload["countries"]


def country_entry(code: str) -> dict | None:
    return load_countries().get(code.upper())


def country_for_timezone(zone_name: str) -> tuple[str, dict] | None:
    for code, entry in load_countries().items():
        if entry.get("timezone") == zone_name:
            return code, entry
    return None


def country_for_locale(locale_name: str) -> tuple[str, dict] | None:
    normalized = locale_name.replace("_", "-")
    parts = normalized.split("-")
    if len(parts) < 2:
        return None
    region = parts[1].upper()
    entry = country_entry(region)
    if entry is None:
        return None
    return region, entry
