"""Android scaffold validation tests."""

from __future__ import annotations

from pathlib import Path

from tools.android.validate_scaffold import REQUIRED_FILES, validate

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_android_scaffold_is_structurally_valid():
    report = validate(REPO_ROOT)
    assert report["status"] == "PASS", report["problems"]
    assert report["kotlin_files"] >= 6


def test_manifest_declares_only_minimal_permissions():
    report = validate(REPO_ROOT)
    permission_check = next(item for item in report["checks"] if item["check"] == "minimal-permissions")
    assert permission_check["passed"] is True


def test_cleartext_traffic_is_forbidden():
    report = validate(REPO_ROOT)
    cleartext = next(item for item in report["checks"] if item["check"] == "cleartext-forbidden")
    assert cleartext["passed"] is True


def test_user_facing_strings_are_english_and_carry_notices():
    report = validate(REPO_ROOT)
    names = {item["check"] for item in report["checks"] if item["passed"]}
    assert {"english-strings", "required-strings"} <= names


def test_every_declared_file_exists():
    missing = [name for name in REQUIRED_FILES if not (REPO_ROOT / "android" / name).is_file()]
    assert missing == []


def test_android_resources_have_no_restricted_branding():
    from tools.scanners.branding_scan import in_user_facing_root, load_branding, scan_text
    from tools.scanners.policy_loader import load_branding as load_branding_policy

    branding = load_branding_policy(REPO_ROOT)
    identifiers = [entry["id"] for entry in branding.get("organization_identifiers", [])]
    android_root = REPO_ROOT / "android"
    violations = []
    for path in sorted(android_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        if not in_user_facing_root(relative, branding):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if scan_text(text, identifiers, relative):
            violations.append(relative)
    assert violations == []
