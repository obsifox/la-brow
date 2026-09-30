"""Detect restricted organization branding in user facing resources."""
from __future__ import annotations

import argparse
import json
import sys
import re
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

from tools.scanners.policy_loader import load_branding

ALLOWED_RESOURCE_PREFIXES = ("about_", "about_us_", "legal_", "copyright_", "license_")
SAFE_CONTEXT_MARKERS = ("data-branding-allowed", "branding-allowed", "legal-notice")


def allowed_path(relative: str, branding: dict) -> bool:
    for pattern in branding.get("allowed_locations", []):
        clean = pattern.rstrip("/")
        if pattern.startswith("document."):
            continue
        if relative.startswith(clean) or relative == clean:
            return True
    return False


def in_user_facing_root(relative: str, branding: dict) -> bool:
    for root in branding.get("user_facing_roots", []):
        clean = root.rstrip("/")
        if relative == clean or relative.startswith(clean + "/"):
            return True
    return False


def scan_text(text: str, identifiers: list[str], relative: str) -> list[dict]:
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        resource_match = re.search(r'name="([^"]+)"', line)
        resource_exempt = bool(resource_match) and resource_match.group(1).startswith(ALLOWED_RESOURCE_PREFIXES)
        context_exempt = any(marker in lowered for marker in SAFE_CONTEXT_MARKERS)
        if resource_exempt or context_exempt:
            continue
        for identifier in identifiers:
            for match in re.finditer(re.escape(identifier), lowered):
                findings.append(
                    {
                        "line": line_number,
                        "column": match.start() + 1,
                        "identifier": identifier,
                        "path": relative,
                    }
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan user facing resources for restricted branding")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    branding = load_branding(repo)
    identifiers = [entry["id"] for entry in branding.get("organization_identifiers", [])]
    report = {
        "scanner": "branding",
        "repo": str(repo),
        "product_name": branding.get("product_name"),
        "organization_identifiers": identifiers,
        "violations": [],
        "scanned_files": 0,
        "skipped_allowed_locations": [],
    }
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(repo).as_posix()
        if set(path.relative_to(repo).parts) & {".git", "__pycache__", ".pytest_cache"}:
            continue
        if not in_user_facing_root(relative, branding):
            continue
        if allowed_path(relative, branding):
            report["skipped_allowed_locations"].append(relative)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        report["scanned_files"] += 1
        findings = scan_text(text, identifiers, relative)
        if findings:
            report["violations"].append({"path": relative, "findings": findings})
    report["violation_count"] = sum(len(item["findings"]) for item in report["violations"])
    report["status"] = "FAIL" if report["violations"] else "PASS"
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"branding_scan status={report['status']} scanned={report['scanned_files']} violations={report['violation_count']}")
    for item in report["violations"][:10]:
        print(f"  {item['path']}: {item['findings'][:3]}")
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
