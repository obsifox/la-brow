"""Verify that the third party resource manifest is complete and consistent."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

import yaml

SOURCE = "docs/licenses/third-party-resources.yaml"
RENDERED = "docs/licenses/THIRD_PARTY_RESOURCES.md"
REJECTED_LOG = "docs/licenses/REJECTED_ALTERNATIVES.md"
ACCEPTED_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "MPL-2.0",
    "ISC",
    "CC0-1.0",
    "public-domain",
    "Unlicense",
    "PSF-2.0",
}
REQUIRED_FIELDS = (
    "name",
    "source",
    "version",
    "license",
    "license_url",
    "purpose",
    "integration_location",
    "modification_status",
    "redistribution_requirements",
    "attribution_requirements",
)
DECLARED_VENDORED_ROOTS = ("tools/eng-orchestrator",)


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(repo: Path) -> dict:
    problems: list[dict] = []
    source_path = repo / SOURCE
    if not source_path.is_file():
        return {"status": "FAIL", "problems": [{"issue": "missing-manifest-source", "path": SOURCE}]}
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    resources = payload.get("resources", [])
    for resource in resources:
        missing = [field for field in REQUIRED_FIELDS if not resource.get(field)]
        if missing:
            problems.append({"resource": resource.get("name"), "issue": "missing-fields", "fields": missing})
        license_name = resource.get("license", "")
        if license_name not in ACCEPTED_LICENSES:
            problems.append({"resource": resource.get("name"), "issue": "license-not-accepted", "license": license_name})
        location = resource.get("integration_location", "")
        target = repo / location
        if "/" not in location and location not in {"repository-wide"}:
            if not target.exists():
                problems.append({"resource": resource.get("name"), "issue": "integration-location-missing", "location": location})
        elif location not in {"repository-wide"} and not target.exists():
            problems.append({"resource": resource.get("name"), "issue": "integration-location-missing", "location": location})
    vendored_names = {resource["name"] for resource in resources if resource.get("modification_status") == "unmodified"}
    for root in DECLARED_VENDORED_ROOTS:
        if (repo / root).is_dir() and not any(resource.get("integration_location") == root for resource in resources):
            problems.append({"issue": "vendored-tree-not-declared", "path": root})
    rendered_path = repo / RENDERED
    if not rendered_path.is_file():
        problems.append({"issue": "rendered-manifest-missing", "path": RENDERED})
    else:
        from tools.license.render_manifest import render

        if rendered_path.read_text(encoding="utf-8") != render(repo):
            problems.append({"issue": "rendered-manifest-out-of-date", "path": RENDERED})
    if not (repo / REJECTED_LOG).is_file():
        problems.append({"issue": "rejected-alternatives-log-missing", "path": REJECTED_LOG})
    manifest_file = repo / "tools/eng-orchestrator/INSTALL_MANIFEST.sha256"
    contract = {
        "resources": len(resources),
        "accepted_licenses": len(ACCEPTED_LICENSES),
        "vendored_trees_declared": len(DECLARED_VENDORED_ROOTS),
        "skill_manifest_present": manifest_file.is_file(),
    }
    return {"status": "PASS" if not problems else "FAIL", "problems": problems, "contract": contract, "vendored": sorted(vendored_names)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the third party resource manifest")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    report = verify(repo)
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"license_manifest status={report['status']} resources={report.get('contract', {}).get('resources', 0)} problems={len(report.get('problems', []))}")
    for problem in report.get("problems", []):
        print(f"  {problem}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
