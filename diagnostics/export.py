"""Diagnostic report builder."""

from __future__ import annotations

from datetime import datetime, timezone as timezone_module

from diagnostics.redaction import DEFAULT_LEVEL, RedactionLevel, redact

APPLICATION_NAME = "LA Brow"


def build_report(environment_snapshot: dict, platform_info: dict | None = None, relevant_tests: list[dict] | None = None) -> dict:
    return {
        "report_version": 1,
        "generated_at": datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "application": {"name": APPLICATION_NAME, "version": environment_snapshot.get("application_version", "0.1.0")},
        "platform": platform_info or {},
        "environment": environment_snapshot,
        "relevant_tests": relevant_tests or [],
        "privacy_notice": "diagnostic export is redacted by default and contains no authentication material",
    }


def export_json(environment_snapshot: dict, level: RedactionLevel = DEFAULT_LEVEL, platform_info: dict | None = None) -> dict:
    report = build_report(environment_snapshot, platform_info)
    return redact(report, level)
