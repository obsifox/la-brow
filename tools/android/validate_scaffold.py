"""Structural validation of the Android application scaffold."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

ANDROID_NAMESPACE = "{http://schemas.android.com/apk/res/android}"
REQUIRED_FILES = (
    "settings.gradle.kts",
    "build.gradle.kts",
    "gradle.properties",
    "app/build.gradle.kts",
    "app/proguard-rules.pro",
    "app/src/main/AndroidManifest.xml",
    "app/src/main/res/xml/network_security_config.xml",
    "app/src/main/res/xml/backup_rules.xml",
    "app/src/main/res/xml/data_extraction_rules.xml",
    "app/src/main/res/values/strings.xml",
    "app/src/main/res/values/themes.xml",
    "app/src/main/res/values/colors.xml",
    "app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml",
    "app/src/main/res/drawable/ic_launcher_background.xml",
    "app/src/main/res/drawable/ic_launcher_foreground.xml",
    "app/src/main/res/drawable/ic_launcher_monochrome.xml",
    "app/src/main/res/raw/dns_providers.json",
    "app/src/main/java/com/labrow/browser/MainActivity.kt",
    "app/src/main/java/com/labrow/browser/core/StorageLayout.kt",
    "app/src/main/java/com/labrow/browser/core/EnvironmentDocument.kt",
    "app/src/main/java/com/labrow/browser/core/EnvironmentRepository.kt",
    "app/src/main/java/com/labrow/browser/core/ProfileRepository.kt",
    "app/src/main/java/com/labrow/browser/core/DnsRepository.kt",
    "app/src/main/java/com/labrow/browser/core/GeckoRuntimeHolder.kt",
    "app/src/main/java/com/labrow/browser/ui/ControlCenterScreen.kt",
)
ALLOWED_PERMISSIONS = {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
}
REQUIRED_STRINGS = (
    "app_name",
    "notice_no_anonymity_guarantee",
    "notice_no_system_dns_change",
    "notice_virtual_mode_no_fallback",
    "label_diagnostics",
    "label_profiles",
)
REQUIRED_KOTLIN_PACKAGE = "com.labrow.browser"
NON_ASCII_ALLOWED = set()
SLASH = chr(47)
STAR = chr(42)


def parse_xml(path: Path, problems: list[dict]) -> ElementTree.Element | None:
    try:
        return ElementTree.parse(path).getroot()
    except ElementTree.ParseError as error:
        problems.append({"file": str(path), "issue": "xml-parse-error", "detail": str(error)})
        return None


def validate(repo: Path) -> dict:
    android_root = repo / "android"
    problems: list[dict] = []
    checks: list[dict] = []

    def record(identifier: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": identifier, "passed": passed, "detail": detail})
        if not passed:
            problems.append({"check": identifier, "detail": detail})

    if not android_root.is_dir():
        record("android-tree", False, "android directory is missing")
        return {"status": "FAIL", "checks": checks, "problems": problems}

    missing = [name for name in REQUIRED_FILES if not (android_root / name).is_file()]
    record("required-files", not missing, ", ".join(missing))

    manifest_root = parse_xml(android_root / "app/src/main/AndroidManifest.xml", problems)
    if manifest_root is not None:
        namespace_value = manifest_root.get("package") or ""
        record("manifest-namespace", namespace_value == "" or namespace_value == REQUIRED_KOTLIN_PACKAGE, namespace_value)
        permissions = {entry.get(ANDROID_NAMESPACE + "name", "") for entry in manifest_root.findall("uses-permission")}
        unexpected = sorted(permissions - ALLOWED_PERMISSIONS)
        record("minimal-permissions", not unexpected, ", ".join(unexpected))
        application = manifest_root.find("application")
        if application is None:
            record("application-node", False, "application node missing")
        else:
            record("backup-disabled", application.get(ANDROID_NAMESPACE + "allowBackup") == "false")
            record("network-security-config", application.get(ANDROID_NAMESPACE + "networkSecurityConfig") == "@xml/network_security_config")
            record("launcher-label-resource", application.get(ANDROID_NAMESPACE + "label") == "@string/app_name")
            record("adaptive-icon", application.get(ANDROID_NAMESPACE + "icon") == "@mipmap/ic_launcher")
        activities = list(manifest_root.iter("activity"))
        record("single-activity", len(activities) == 1, str(len(activities)))
        if activities:
            activity = activities[0]
            record("activity-exported", activity.get(ANDROID_NAMESPACE + "exported") == "true")
            actions = {intent.get(ANDROID_NAMESPACE + "name") for intent in activity.iter("action")}
            record("launcher-intent", "android.intent.action.MAIN" in actions)
            record("browsable-intent", "android.intent.action.VIEW" in actions)

    network_config = parse_xml(android_root / "app/src/main/res/xml/network_security_config.xml", problems)
    if network_config is not None:
        base_config = network_config.find("base-config")
        record(
            "cleartext-forbidden",
            base_config is not None and base_config.get("cleartextTrafficPermitted") == "false",
        )

    strings_root = parse_xml(android_root / "app/src/main/res/values/strings.xml", problems)
    if strings_root is not None:
        entries = {entry.get("name"): (entry.text or "") for entry in strings_root.findall("string")}
        missing_strings = [name for name in REQUIRED_STRINGS if name not in entries]
        record("required-strings", not missing_strings, ", ".join(missing_strings))
        non_ascii = {
            name: [character for character in value if ord(character) > 127 and ord(character) not in NON_ASCII_ALLOWED]
            for name, value in entries.items()
        }
        offending = {name: characters for name, characters in non_ascii.items() if characters}
        record("english-strings", not offending, json.dumps(offending))

    adaptive_icon = parse_xml(android_root / "app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", problems)
    if adaptive_icon is not None:
        children = {child.tag for child in adaptive_icon}
        record("adaptive-icon-layers", {"background", "foreground", "monochrome"} <= children, ", ".join(sorted(children)))

    kotlin_files = sorted((android_root / "app/src/main/java").rglob("*.kt"))
    record("kotlin-file-count", len(kotlin_files) >= 6, str(len(kotlin_files)))
    comment_violations = []
    package_violations = []
    for path in kotlin_files:
        text = path.read_text(encoding="utf-8")
        if SLASH * 2 in text or SLASH + STAR in text:
            comment_violations.append(str(path.relative_to(android_root)))
        if REQUIRED_KOTLIN_PACKAGE not in text.splitlines()[0]:
            package_violations.append(str(path.relative_to(android_root)))
    record("kotlin-no-comments", not comment_violations, ", ".join(comment_violations))
    record("kotlin-package-declarations", not package_violations, ", ".join(package_violations))

    build_file = (android_root / "app/build.gradle.kts").read_text(encoding="utf-8")
    record("geckoview-dependency", "org.mozilla.geckoview:geckoview" in build_file)
    record("compose-enabled", "compose = true" in build_file)
    record("release-minify", "isMinifyEnabled = true" in build_file)

    resolver_payload = json.loads((android_root / "app/src/main/res/raw/dns_providers.json").read_text(encoding="utf-8"))
    provider_ids = {entry["id"] for entry in resolver_payload.get("providers", [])}
    record("resolver-profiles-bundled", {"system", "cloudflare-doh", "quad9-dot"} <= provider_ids, ", ".join(sorted(provider_ids)))
    record("resolver-policy", resolver_payload.get("policy", {}).get("os_wide_changes") == "forbidden")

    storage_source = (android_root / "app/src/main/java/com/labrow/browser/core/StorageLayout.kt").read_text(encoding="utf-8")
    record("storage-layout-directories", all(token in storage_source for token in ('"profiles"', '"settings"', '"diagnostics"', '"cache"')))
    record("storage-layout-identifier-pattern", bool(re.search(r"Regex\(", storage_source)))

    status = "PASS" if not problems else "FAIL"
    return {"status": status, "checks": checks, "problems": problems, "kotlin_files": len(kotlin_files)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Android application scaffold")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    parser.add_argument("--verbose", action="store_true")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    report = validate(repo)
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"android_scaffold status={report['status']} checks={len(report.get('checks', []))} problems={len(report.get('problems', []))}")
    if arguments.verbose or report["status"] == "FAIL":
        for item in report.get("checks", []):
            marker = "ok" if item["passed"] else "fail"
            print(f"  {marker:<4} {item['check']}{'' if item['passed'] else ': ' + item['detail']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
