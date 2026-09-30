"""Verify or install the required engineering orchestration skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONFIG_PATH = "config/engineering/required-skills.yaml"


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_config(repo: Path) -> dict:
    config_path = repo / CONFIG_PATH
    if not config_path.is_file():
        raise SystemExit(f"missing skill configuration: {CONFIG_PATH}")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


class Installer:
    def __init__(self, repo: Path, skill: dict) -> None:
        self.repo = repo
        self.skill = skill
        self.install_path = repo / skill["install_path"]

    def install(self) -> list[str]:
        log: list[str] = []
        if self.install_path.exists():
            shutil.rmtree(self.install_path)
        self.install_path.mkdir(parents=True, exist_ok=True)
        staging = self.install_path.parent / "_skill-staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        commands = [
            ["git", "init", "--quiet"],
            ["git", "remote", "add", "origin", self.skill["repository"]],
            ["git", "fetch", "--quiet", "--depth", "1", "origin", self.skill["revision"]],
            ["git", "checkout", "--quiet", "FETCH_HEAD"],
        ]
        for command in commands:
            result = subprocess.run(command, cwd=staging, capture_output=True, text=True, timeout=300)
            log.append(f"{' '.join(command)} exit={result.returncode}")
            if result.returncode != 0:
                raise SystemExit(f"install step failed: {' '.join(command)}\n{result.stderr.strip()}")
        for item in sorted(staging.iterdir()):
            if item.name == ".git":
                continue
            target = self.install_path / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        shutil.rmtree(staging)
        log.append(f"installed {self.skill['id']} at {self.skill['revision']}")
        return log


def verify(repo: Path, skill: dict) -> dict:
    install_path = repo / skill["install_path"]
    report = {"id": skill["id"], "expected_revision": skill["revision"], "install_path": str(skill["install_path"])}
    errors: list[str] = []
    if not install_path.is_dir():
        errors.append("install path missing")
        report["status"] = "MISSING"
        report["errors"] = errors
        return report
    verification = skill.get("verification", {})
    missing = [name for name in verification.get("required_files", []) if not (install_path / name).is_file()]
    if missing:
        errors.append("missing required files: " + ", ".join(missing))
    manifest_name = skill.get("verification", {}).get("manifest")
    manifest_summary = {"entries": 0, "mismatched": [], "missing": [], "path": manifest_name}
    if manifest_name:
        manifest_path = repo / manifest_name
        if not manifest_path.is_file():
            errors.append(f"manifest missing: {manifest_name}")
        else:
            mismatched: list[str] = []
            absent: list[str] = []
            entries = 0
            for line in manifest_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                expected, _, relative = line.partition("  ")
                entries += 1
                target = install_path / relative
                if not target.is_file():
                    absent.append(relative)
                elif sha256_file(target) != expected:
                    mismatched.append(relative)
            manifest_summary.update({"entries": entries, "mismatched": mismatched, "missing": absent})
            if mismatched:
                errors.append(f"manifest mismatch: {len(mismatched)} files")
    version_file = install_path / "SKILL.md"
    detected_version = None
    if version_file.is_file():
        for line in version_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                detected_version = line.split(":", 1)[1].strip()
                break
    minimum = verification.get("min_skill_version")
    version_ok = True
    if minimum and detected_version:
        def as_tuple(value: str) -> tuple:
            return tuple(int(part) for part in value.split(".") if part.isdigit())
        version_ok = as_tuple(detected_version) >= as_tuple(minimum)
    if not version_ok:
        errors.append(f"skill version {detected_version} below minimum {minimum}")
    report.update(
        {
            "detected_version": detected_version,
            "version_ok": version_ok,
            "manifest": manifest_summary,
            "errors": errors,
            "status": "VERIFIED" if not errors else "FAILED",
        }
    )
    return report


def write_state(repo: Path, skill: dict, report: dict, install_log: list[str]) -> Path:
    state_path = repo / skill.get("registry_state", ".eng/bootstrap-state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if state_path.is_file():
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    skills = {entry["id"]: entry for entry in existing.get("skills", [])}
    skills[skill["id"]] = {
        "id": skill["id"],
        "repository": skill["repository"],
        "revision": skill["revision"],
        "detected_version": report.get("detected_version"),
        "status": report["status"],
        "install_path": skill["install_path"],
        "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "required_files_ok": not any("required files" in error for error in report.get("errors", [])),
        "manifest_entries": report.get("manifest", {}).get("entries", 0),
        "install_log": install_log,
        "read_after_install": skill.get("read_after_install", []),
    }
    existing["skills"] = list(skills.values())
    existing["schema_version"] = 1
    existing["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state_path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the required engineering orchestration skill")
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--install", action="store_true", help="install the pinned revision when missing or broken")
    parser.add_argument("--json", action="store_true", help="emit machine readable output")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    config = load_config(repo)
    exit_code = 0
    results = []
    for skill in config["required_skills"]:
        install_log: list[str] = []
        report = verify(repo, skill)
        if report["status"] != "VERIFIED" and arguments.install and skill.get("auto_install"):
            installer = Installer(repo, skill)
            install_log = installer.install()
            subprocess.run(
                [sys.executable, "tools/agent/generate_manifest.py", "--root", skill["install_path"], "--out", skill["verification"]["manifest"]],
                cwd=repo,
                check=True,
            )
            report = verify(repo, skill)
            report["installed"] = True
        if report["status"] != "VERIFIED":
            exit_code = 1
        write_state(repo, skill, report, install_log)
        results.append(report)
    payload = {"skills": results, "status": "VERIFIED" if exit_code == 0 else "FAILED"}
    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        for report in results:
            print(f"skill {report['id']} status={report['status']} version={report.get('detected_version')}")
            for error in report.get("errors", []):
                print(f"  error: {error}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
