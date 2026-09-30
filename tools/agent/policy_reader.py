"""Read and summarize the project policies that govern engineering work."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

POLICY_FILES = (
    "config/engineering/project.yaml",
    "config/engineering/required-skills.yaml",
    "config/engineering/resource-policy.yaml",
    "config/engineering/code-style.yaml",
    "config/engineering/branding-policy.yaml",
    "config/engineering/orchestration.yaml",
    "config/browser/defaults.yaml",
    "config/network/dns-providers.yaml",
    "config/build/targets.yaml",
)


def summarize(repo: Path) -> dict:
    summary = {"policies": [], "rules": []}
    for relative in POLICY_FILES:
        path = repo / relative
        if not path.is_file():
            summary["policies"].append({"file": relative, "present": False})
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        summary["policies"].append({"file": relative, "present": True, "top_level_keys": sorted(payload)})
    code_style = yaml.safe_load((repo / "config/engineering/code-style.yaml").read_text(encoding="utf-8"))
    project = yaml.safe_load((repo / "config/engineering/project.yaml").read_text(encoding="utf-8"))
    branding = yaml.safe_load((repo / "config/engineering/branding-policy.yaml").read_text(encoding="utf-8"))
    summary["rules"] = [
        f"comments: {code_style['policy']['comments']['default']}",
        f"emoji: {code_style['policy']['emoji']['default']}",
        f"language: {code_style['policy']['language']['default']}",
        f"branding: {branding['policy'] if 'policy' in branding else code_style['policy']['branding']['default']}",
        f"product name: {branding['product_name']}",
        f"organization identifiers restricted: {len(branding['organization_identifiers'])}",
        f"english only: {project['project']['english_only']}",
        f"source comments allowed: {project['project']['source_comments_allowed']}",
        f"declared exemptions: {len(code_style.get('exemptions', []))}",
    ]
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Read project policies")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    summary = summarize(repo)
    if arguments.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    for entry in summary["policies"]:
        state = "present" if entry["present"] else "missing"
        keys = ", ".join(entry.get("top_level_keys", []))
        print(f"{entry['file']:<48} {state:<8} {keys}")
    print("")
    for rule in summary["rules"]:
        print(f"rule: {rule}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
