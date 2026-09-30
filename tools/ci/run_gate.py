"""Execute the continuous integration pipeline stages and report results."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone as timezone_module
from pathlib import Path

import yaml

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

PIPELINE = "ci/pipeline.yml"


def load_stages(repo: Path) -> list[dict]:
    payload = yaml.safe_load((repo / PIPELINE).read_text(encoding="utf-8"))
    return payload["stages"]


def run_stage(repo: Path, stage: dict, timeout: int) -> dict:
    completed = subprocess.run(
        stage["command"],
        cwd=repo,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = (completed.stdout or "").strip().splitlines()
    errors = (completed.stderr or "").strip().splitlines()
    return {
        "id": stage["id"],
        "command": stage["command"],
        "exit_code": completed.returncode,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "stdout_tail": output[-6:],
        "stderr_tail": errors[-6:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the validation pipeline")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--only", action="append", help="run only the named stage")
    parser.add_argument("--json-out", default=".eng/artifacts/ci_report.json")
    parser.add_argument("--timeout", type=int, default=600)
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    stages = load_stages(repo)
    if arguments.only:
        stages = [stage for stage in stages if stage["id"] in arguments.only]
    results = []
    exit_code = 0
    started = datetime.now(timezone_module.utc)
    for stage in stages:
        result = run_stage(repo, stage, arguments.timeout)
        results.append(result)
        marker = "PASS" if result["status"] == "PASS" else "FAIL"
        print(f"{stage['id']:<22} {marker} exit={result['exit_code']}")
        if result["status"] == "FAIL":
            exit_code = 1
            for line in result["stdout_tail"][-4:]:
                print(f"    {line}")
            for line in result["stderr_tail"][-4:]:
                print(f"    {line}")
    report = {
        "generated_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round((datetime.now(timezone_module.utc) - started).total_seconds(), 2),
        "status": "PASS" if exit_code == 0 else "FAIL",
        "stages": results,
    }
    target = repo / arguments.json_out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"pipeline status={report['status']} stages={len(results)} duration_seconds={report['duration_seconds']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
