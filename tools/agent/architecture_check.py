"""Verify that the documented architecture baseline exists and matches the repository."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

REQUIRED_DOCUMENTS = (
    "docs/architecture/system-architecture.md",
    "docs/architecture/environment-report.md",
    "docs/architecture/gecko-integration.md",
    "docs/architecture/geo-architecture.md",
    "docs/architecture/network-architecture.md",
    "docs/architecture/dns-architecture.md",
    "docs/architecture/profile-architecture.md",
    "docs/architecture/android-architecture.md",
    "docs/architecture/desktop-architecture.md",
    "docs/security/threat-model.md",
    "docs/security/security-boundaries.md",
    "docs/security/network-security.md",
    "docs/security/profile-security.md",
    "docs/security/update-security.md",
    "docs/testing/test-strategy.md",
    "docs/testing/geo-test-matrix.md",
    "docs/testing/dns-test-matrix.md",
    "docs/testing/browser-test-matrix.md",
    "docs/testing/security-test-matrix.md",
    "docs/releases/release-process.md",
    "docs/releases/reproducible-builds.md",
    "docs/releases/compatibility-matrix.md",
    "docs/operations/diagnostics.md",
    "docs/operations/recovery.md",
    "docs/operations/troubleshooting.md",
)

REQUIRED_MODULES = (
    "geo/engine.py",
    "geo/providers.py",
    "geo/state.py",
    "timezone/engine.py",
    "locale_engine/engine.py",
    "dns/engine.py",
    "dns/wire.py",
    "doh/client.py",
    "dot/client.py",
    "profiles/store.py",
    "profiles/migrations.py",
    "policy/engine.py",
    "privacy/policy.py",
    "webrtc/policy.py",
    "diagnostics/consistency.py",
    "environment/core.py",
    "gecko/integration.py",
    "browser/shell.py",
    "application/service.py",
)

FORBIDDEN_DEPENDENCY_DIRECTIONS = (
    {
        "source_prefix": "geo/",
        "forbidden_imports": ("from browser", "import browser", "from application", "import application"),
        "reason": "the geo engine must not depend on the user interface or the application layer",
    },
    {
        "source_prefix": "dns/",
        "forbidden_imports": ("from profiles", "import profiles", "from policy", "import policy"),
        "reason": "the DNS engine must not own the profile engine or the policy engine",
    },
)


def check(repo: Path) -> dict:
    missing_documents = [name for name in REQUIRED_DOCUMENTS if not (repo / name).is_file()]
    missing_modules = [name for name in REQUIRED_MODULES if not (repo / name).is_file()]
    direction_violations = []
    for rule in FORBIDDEN_DEPENDENCY_DIRECTIONS:
        for path in sorted((repo / rule["source_prefix"]).rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in rule["forbidden_imports"]:
                if token in text:
                    direction_violations.append(
                        {
                            "file": path.relative_to(repo).as_posix(),
                            "token": token,
                            "reason": rule["reason"],
                        }
                    )
    report = {
        "status": "PASS" if not (missing_documents or missing_modules or direction_violations) else "FAIL",
        "documented_documents": len(REQUIRED_DOCUMENTS) - len(missing_documents),
        "documented_documents_total": len(REQUIRED_DOCUMENTS),
        "missing_documents": missing_documents,
        "modules_present": len(REQUIRED_MODULES) - len(missing_modules),
        "missing_modules": missing_modules,
        "dependency_direction_violations": direction_violations,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the architecture baseline")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    report = check(repo)
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"architecture_check status={report['status']} documents={report['documented_documents']}/{report['documented_documents_total']} "
        f"modules={report['modules_present']}/{len(REQUIRED_MODULES)} direction_violations={len(report['dependency_direction_violations'])}"
    )
    for name in report["missing_documents"]:
        print(f"  missing document: {name}")
    for name in report["missing_modules"]:
        print(f"  missing module: {name}")
    for violation in report["dependency_direction_violations"]:
        print(f"  direction violation: {violation['file']} -> {violation['token']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
