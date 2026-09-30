"""Deterministic Gecko preference and policy artifact generation."""

from __future__ import annotations

import json

PREFERENCE_ORDER = (
    "environment.",
    "intl.",
    "javascript.",
    "general.",
    "privacy.",
    "network.",
    "media.",
    "permissions.",
    "dom.",
    "dns.",
)


def sort_preferences(preferences: dict) -> list[tuple[str, object]]:
    def key(item: tuple[str, object]) -> tuple:
        name = item[0]
        rank = len(PREFERENCE_ORDER)
        for index, prefix in enumerate(PREFERENCE_ORDER):
            if name.startswith(prefix):
                rank = index
                break
        return (rank, name)

    return sorted(preferences.items(), key=key)


def render_preference(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def render_user_js(preferences: dict) -> str:
    lines = []
    for name, value in sort_preferences(preferences):
        lines.append(f'user_pref("{name}", {render_preference(value)});')
    return "\n".join(lines) + "\n"


def render_policies_json(doh_endpoint: str | None, doh_enabled: bool, locked: bool = True, fallback: bool = False) -> str:
    policies: dict = {"Preferences": {}}
    if doh_endpoint:
        policies["DNSOverHTTPS"] = {
            "Enabled": bool(doh_enabled),
            "ProviderURL": doh_endpoint,
            "Locked": bool(locked),
            "Fallback": bool(fallback),
        }
    return json.dumps({"policies": policies}, indent=2, sort_keys=True) + "\n"
