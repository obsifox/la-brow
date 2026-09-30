#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
mkdir -p .eng/artifacts
echo "step 1 inspect environment"
python3 tools/agent/environment_report.py --out docs/architecture/environment-report.md --json .eng/artifacts/environment.json
echo "step 2 verify required engineering skill"
python3 tools/agent/verify_skill.py --repo . --install --json | tee .eng/artifacts/skill_verification.json
echo "step 3 validate skill registry"
bash tools/eng-orchestrator/scripts/skill_registry.sh discover || echo "warning: skill registry discover returned non zero"
echo "step 4 validate project profile"
bash tools/eng-orchestrator/scripts/project_profile.sh --check
echo "step 5 read project policies"
python3 tools/agent/policy_reader.py --repo .
echo "step 6 resource discovery manifest"
python3 tools/license/verify_manifest.py --repo .
echo "step 7 architecture baseline presence"
python3 tools/agent/architecture_check.py --repo .
echo "step 8 static scans"
python3 tools/scanners/run_all_scans.py --repo .
echo "bootstrap complete"
