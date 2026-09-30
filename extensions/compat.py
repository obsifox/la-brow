"""Compatibility evaluation for desktop Firefox themes and extensions."""

from __future__ import annotations

from pathlib import Path

import yaml

from extensions.manifest import SECTION_ALIASES, WebExtensionManifest

MATRIX_PATH = Path("config/compat/firefox-desktop-apis.yaml")
LEVEL_ORDER = ("supported", "partial", "unsupported")

SEVERITY_BY_LEVEL = {
    "supported": "INFO",
    "partial": "NOTICE",
    "unsupported": "WARN",
}


class CompatibilityEngine:
    """Evaluates a parsed manifest against the declared runtime matrix."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.matrix = yaml.safe_load((repo / MATRIX_PATH).read_text(encoding="utf-8"))
        self.sections = {entry["section"]: entry for entry in self.matrix.get("sections", [])}
        self.permissions = {entry["permission"]: entry for entry in self.matrix.get("permissions", [])}
        self.weights = self.matrix.get("counters", {})

    def runtime(self) -> dict:
        return dict(self.matrix.get("runtime", {}))

    def notice(self) -> str:
        return str(self.matrix.get("install_notice", ""))

    def matrix_summary(self) -> dict:
        return {
            "runtime": self.runtime(),
            "sections": sorted(self.sections.values(), key=lambda entry: entry["section"]),
            "permissions": sorted(self.permissions.values(), key=lambda entry: entry["permission"]),
            "install_notice": self.notice(),
        }

    def _level_for_section(self, section: str) -> dict:
        key = SECTION_ALIASES.get(section, section)
        entry = self.sections.get(key)
        if entry is None:
            return {"section": section, "level": "partial", "note": "no matrix entry, treated as partial"}
        return {"section": section, "level": entry.get("level", "partial"), "note": entry.get("note", "")}

    def _level_for_permission(self, permission: str) -> dict:
        entry = self.permissions.get(permission)
        if entry is None:
            return {"permission": permission, "level": "partial", "note": "unclassified permission, treated as partial"}
        return {"permission": permission, "level": entry.get("level", "partial"), "note": entry.get("note", "")}

    def _score(self, levels: list[str]) -> float:
        if not levels:
            return 1.0
        weights = {
            "supported": float(self.weights.get("supported_weight", 1.0)),
            "partial": float(self.weights.get("partial_weight", 0.5)),
            "unsupported": float(self.weights.get("unsupported_weight", 0.0)),
        }
        return round(sum(weights[level] for level in levels) / len(levels), 4)

    def _level_name(self, score: float) -> str:
        if score >= float(self.weights.get("compatible_threshold", 0.85)):
            return "COMPATIBLE"
        if score >= float(self.weights.get("partial_threshold", 0.4)):
            return "PARTIAL"
        return "NOT_SUPPORTED"

    def evaluate(self, manifest: WebExtensionManifest) -> dict:
        section_items = [self._level_for_section(section) for section in manifest.declared_sections]
        permission_items = [self._level_for_permission(permission) for permission in manifest.declared_permissions()]
        levels = [item["level"] for item in section_items + permission_items]
        score = self._score(levels)
        findings: list[dict] = []
        for item in section_items:
            if item["level"] == "unsupported":
                findings.append(
                    {
                        "code": "desktop-only-section",
                        "severity": SEVERITY_BY_LEVEL["unsupported"],
                        "message": f"the manifest declares {item['section']}, which the mobile runtime cannot honour",
                        "detail": item.get("note", ""),
                    }
                )
            elif item["level"] == "partial":
                findings.append(
                    {
                        "code": "partial-section",
                        "severity": SEVERITY_BY_LEVEL["partial"],
                        "message": f"the manifest declares {item['section']}, which is applied on a best effort basis",
                        "detail": item.get("note", ""),
                    }
                )
        for item in permission_items:
            if item["level"] == "unsupported":
                findings.append(
                    {
                        "code": "unsupported-permission",
                        "severity": SEVERITY_BY_LEVEL["unsupported"],
                        "message": f"the manifest requests {item['permission']}, which is not granted on the mobile runtime",
                        "detail": item.get("note", ""),
                    }
                )
            elif item["level"] == "partial":
                findings.append(
                    {
                        "code": "partial-permission",
                        "severity": SEVERITY_BY_LEVEL["partial"],
                        "message": f"the manifest requests {item['permission']}, which behaves differently on the mobile runtime",
                        "detail": item.get("note", ""),
                    }
                )
        return {
            "level": self._level_name(score),
            "score": score,
            "runtime": self.runtime(),
            "manifest": manifest.as_record(),
            "sections": section_items,
            "permissions": permission_items,
            "findings": findings,
            "counts": {
                "supported": levels.count("supported"),
                "partial": levels.count("partial"),
                "unsupported": levels.count("unsupported"),
            },
            "notice": self.notice(),
            "notice_required_at_install": True,
        }
