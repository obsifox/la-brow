"""Build the self contained control center preview from real pipeline output."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone as timezone_module
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

from application.service import EnvironmentService

SCENARIOS = (
    {
        "id": "berlin-policy",
        "label": "Berlin manual with site policy",
        "url": "https://example.com/page",
        "profile": "default",
        "resolver": None,
        "privacy": "balanced",
        "private": False,
        "description": "Manual virtual location in Berlin with a site policy that overrides timezone and locale for the example.com domain.",
    },
    {
        "id": "tokyo-private",
        "label": "Tokyo manual in private browsing",
        "url": "https://example.com/page",
        "profile": "tokyo",
        "resolver": None,
        "privacy": "strict",
        "private": True,
        "description": "Manual virtual location in Tokyo with per query randomization selected by the private browsing policy rule and the strict privacy preset.",
    },
    {
        "id": "hamburg-dns",
        "label": "Hamburg hybrid with encrypted resolver",
        "url": "https://example.org/portal",
        "profile": "hamburg",
        "resolver": "cloudflare-doh",
        "privacy": "balanced",
        "private": False,
        "description": "Hybrid location that combines an automatic country base with manual city and radius, plus a DNS over HTTPS resolver profile that never validates in this environment.",
    },
)

PROFILES = {
    "tokyo": {
        "name": "tokyo",
        "profile_version": 2,
        "geolocation_mode": "manual",
        "country": "JP",
        "city": "Tokyo",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "radius": 8000,
        "accuracy_m": 8000,
        "randomization": "per_query",
        "randomization_seed": 20260214,
        "timezone": "Asia/Tokyo",
        "locale": "ja-JP",
        "languages": ["ja-JP", "en-US"],
        "webrtc_policy": "disable_local_candidates",
    },
    "hamburg": {
        "name": "hamburg",
        "profile_version": 2,
        "geolocation_mode": "hybrid",
        "country": "DE",
        "city": "Hamburg",
        "latitude": 53.5511,
        "longitude": 9.9937,
        "radius": 12000,
        "accuracy_m": 12000,
        "randomization": "per_session",
        "randomization_seed": 77,
        "timezone": "Europe/Berlin",
        "locale": "de-DE",
        "languages": ["de-DE", "en-US"],
        "webrtc_policy": "privacy_enhanced",
    },
}


def run_scans(repo: Path) -> dict:
    results = {}
    for name in ("emoji", "comment", "english", "branding"):
        completed = subprocess.run(
            [sys.executable, f"tools/scanners/{name}_scan.py", "--repo", "."],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=300,
        )
        first_line = (completed.stdout or "").strip().splitlines()
        results[name] = {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "summary": first_line[0] if first_line else "no output",
        }
    return results


def run_test_summary(repo: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--tb=no", "-p", "no:cacheprovider"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=900,
    )
    lines = [line for line in (completed.stdout or "").strip().splitlines() if line.strip()]
    summary_line = lines[-1] if lines else "no output"
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for token in summary_line.replace(",", " ").split():
        pass
    import re

    for key in counts:
        match = re.search(rf"(\d+) {key}", summary_line)
        if match:
            counts[key] = int(match.group(1))
    return {"status": "PASS" if completed.returncode == 0 else "FAIL", "summary": summary_line, "counts": counts}


def collect(repo: Path) -> dict:
    service = EnvironmentService(repo)
    scenarios = []
    for scenario in SCENARIOS:
        if scenario["profile"] in PROFILES:
            saved = service.store.save(PROFILES[scenario["profile"]], scenario["profile"])
            scenario = dict(scenario, profile_path=saved["path"])
        snapshot = service.resolve(
            url=scenario["url"],
            profile_id=scenario["profile"],
            resolver_id=scenario["resolver"],
            privacy_preset=scenario["privacy"],
            private_browsing=scenario["private"],
        )
        redacted = service.diagnostics_export("redacted", profile_id=scenario["profile"])
        minimal = service.diagnostics_export("minimal", profile_id=scenario["profile"])
        scenarios.append(
            {
                "id": scenario["id"],
                "label": scenario["label"],
                "description": scenario["description"],
                "url": scenario["url"],
                "private_browsing": scenario["private"],
                "resolver": scenario["resolver"],
                "snapshot": snapshot,
                "diagnostics_redacted": redacted,
                "diagnostics_minimal": minimal,
            }
        )
    resolver_profiles = [profile.as_dict() for profile in service.resolver_profiles.values()]
    identities = json.loads((repo / "assets/identity/identity-report.json").read_text(encoding="utf-8"))
    licenses = (repo / "docs/licenses/THIRD_PARTY_RESOURCES.md").read_text(encoding="utf-8")
    return {
        "generated_at": datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "application": {"name": "LA Brow", "version": "0.1.0", "schema": 1},
        "scenarios": scenarios,
        "resolver_profiles": resolver_profiles,
        "scans": run_scans(repo),
        "tests": run_test_summary(repo),
        "identity": {
            "viewbox": identities["viewbox"],
            "palette": identities["palette"],
            "rasters": identities["rasters"],
            "eye_visibility": identities["eye_visibility"],
            "icon": (repo / "assets/identity/icon.svg").read_text(encoding="utf-8"),
            "symbol": (repo / "assets/identity/icon-symbol.svg").read_text(encoding="utf-8"),
            "mask": (repo / "assets/identity/icon-mask.svg").read_text(encoding="utf-8"),
            "monochrome": (repo / "assets/identity/icon-monochrome.svg").read_text(encoding="utf-8"),
        },
        "licenses": licenses,
        "stage_order": scenarios[0]["snapshot"]["stage_order"],
        "roadmap": roadmap(repo),
        "orchestration": orchestration(repo),
    }


def orchestration(repo: Path) -> dict:
    state_path = repo / ".eng/state.json"
    gates = {}
    if state_path.is_file():
        gates = json.loads(state_path.read_text(encoding="utf-8")).get("gates", {})
    ci_path = repo / ".eng/artifacts/ci_report.json"
    ci = {}
    if ci_path.is_file():
        ci = json.loads(ci_path.read_text(encoding="utf-8"))
    review_path = repo / ".eng/artifacts/code_review.md"
    findings = []
    if review_path.is_file():
        for line in review_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                findings.append(line[4:])
    skill_state_path = repo / ".eng/bootstrap-state.json"
    skill = {}
    if skill_state_path.is_file():
        payload = json.loads(skill_state_path.read_text(encoding="utf-8"))
        if payload.get("skills"):
            skill = payload["skills"][0]
    return {
        "gates": gates,
        "ci": {"status": ci.get("status"), "duration_seconds": ci.get("duration_seconds"), "stages": len(ci.get("stages", []))},
        "review_findings": findings,
        "skill": {
            "id": skill.get("id"),
            "revision": skill.get("revision"),
            "version": skill.get("detected_version"),
            "status": skill.get("status"),
            "manifest_entries": skill.get("manifest_entries"),
        },
        "run_id": "RUN-2026-000001",
    }


def roadmap(repo: Path) -> list[dict]:
    return [
        {"milestone": "M0 engineering bootstrap", "status": "DONE", "note": "Repository, pinned orchestration skill, policy scanners, pipeline, license manifest."},
        {"milestone": "M1 environment core", "status": "DONE", "note": "Eleven stage deterministic pipeline with stage status and invariants."},
        {"milestone": "M2 geo engine", "status": "DONE", "note": "Manual, automatic, hybrid, disabled providers with radius randomization and seeds."},
        {"milestone": "M3 timezone and locale", "status": "DONE", "note": "IANA based offsets and daylight saving plus five separated locale surfaces."},
        {"milestone": "M4 DNS, DoH, DoT", "status": "DONE", "note": "Codec, system transport with TCP retry, HTTPS and TLS clients tested against local servers."},
        {"milestone": "M5 profiles", "status": "DONE", "note": "Versioning, migration, integrity, import, export, rollback."},
        {"milestone": "M6 automatic and hybrid", "status": "DONE", "note": "Coarse proposals with confidence, notes and manual override transparency."},
        {"milestone": "M7 privacy and diagnostics", "status": "DONE", "note": "Consistency findings, redaction levels, structured events."},
        {"milestone": "M8 desktop production build", "status": "SCAFFOLDED", "note": "Requires the engine toolchain which is absent in the measured environment."},
        {"milestone": "M9 android production build", "status": "SCAFFOLDED", "note": "Scaffold validated by twenty checks; assembly requires Android SDK and Gradle."},
        {"milestone": "M10 security and release certification", "status": "PARTIAL", "note": "Threat model, boundaries and scanners complete; signing pipeline planned with packaging."},
        {"milestone": "Identity system", "status": "DONE", "note": "Six vector assets plus raster legibility validation from 16 to 1024 pixels."},
    ]


def render_html(data: dict, template: str) -> str:
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
    return template.replace("__DEMO_DATA__", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the control center preview")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", default="demo/labrow-control-center.html")
    parser.add_argument("--json-out", default="demo/data.json")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    data = collect(repo)
    template = (repo / "tools/dev/control_center_template.html").read_text(encoding="utf-8")
    output = render_html(data, template)
    target = repo / arguments.out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output, encoding="utf-8")
    (repo / arguments.json_out).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"control center written to {target} ({len(output)} bytes)")
    print(f"scenarios={len(data['scenarios'])} tests={data['tests']['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
