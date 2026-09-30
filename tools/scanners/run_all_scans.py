"""Run every static policy scanner and aggregate the result."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCANNERS = [
    ("emoji", "tools/scanners/emoji_scan.py"),
    ("comment", "tools/scanners/comment_scan.py"),
    ("english", "tools/scanners/english_scan.py"),
    ("branding", "tools/scanners/branding_scan.py"),
    ("license", "tools/license/verify_manifest.py"),
    ("android", "tools/android/validate_scaffold.py"),
    ("skill", "tools/agent/verify_skill.py"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all static policy scans")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out", default=".eng/artifacts/static_scans.json")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    artifacts = repo / ".eng/artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    results = []
    exit_code = 0
    for name, script in SCANNERS:
        command = [sys.executable, script, "--repo", str(repo)]
        if name in {"emoji", "comment", "english", "branding"}:
            command += ["--json-out", str(artifacts / f"{name}_scan.json")]
        completed = subprocess.run(command, cwd=repo, capture_output=True, text=True)
        status = "PASS" if completed.returncode == 0 else "FAIL"
        if completed.returncode != 0:
            exit_code = 1
        results.append(
            {
                "scanner": name,
                "script": script,
                "status": status,
                "exit_code": completed.returncode,
                "stdout": completed.stdout.strip().splitlines()[:12],
                "stderr": completed.stderr.strip().splitlines()[:12],
            }
        )
    report = {"status": "PASS" if exit_code == 0 else "FAIL", "scanners": results}
    Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for item in results:
        print(f"{item['scanner']:<10} {item['status']} exit={item['exit_code']}")
        if item["status"] == "FAIL":
            for line in item["stdout"]:
                print(f"    {line}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
