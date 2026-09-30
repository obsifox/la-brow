# Reproducible Builds

## Requirement

A build is reproducible when two independent builds from the same recorded inputs produce byte identical artifacts, or when the differences are enumerated and explained.

## Recorded Inputs

| Input | Where Recorded |
| --- | --- |
| Source revision | Version control identifier |
| Compiler versions | `docs/architecture/environment-report.md` and the build host report |
| Engine revision | Pinned in the build configuration |
| Vendored dependency revision | `config/engineering/required-skills.yaml` and the integrity manifest |
| Dependency versions | `config/build/targets.yaml` and the resolver configuration |
| Build flags | Recorded in the build log |
| Build environment | Host report produced by `tools/agent/environment_report.py` |

## Artifact Hashing

Every artifact is recorded with a cryptographic hash in `build/artifacts.sha256` when a packaging stage exists. The identity generator already records per file hashes in `assets/identity/identity-report.json`, which demonstrates the pattern.

## Current Status

No browser artifact is produced in this environment. Reproducibility therefore applies today to the deterministic generator outputs:

- Identity assets are generated from a fixed geometry definition and validated for legibility at every size
- Gecko integration artifacts are ordered deterministically, asserted by unit tests
- Profile migrations are pure functions of the input document, asserted by unit tests

## Verification Procedure For A Future Build

1. Record the environment report on the build host
2. Build twice from the same revision with the same flags
3. Compare artifact hashes
4. If hashes differ, enumerate the differences and classify each as explained or unexplained
5. Publish the comparison in the release notes
