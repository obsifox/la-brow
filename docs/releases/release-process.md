# Release Process

## Channels

| Channel | Purpose | Update Configuration |
| --- | --- | --- |
| Nightly | Continuous integration artifacts | Separate metadata, unsigned development builds are never distributed |
| Stable | Supported release | Signed packages published by the release workflow on a version tag |
| Development | Feature complete, not verified | Separate metadata |
| Beta | Release candidate verification | Separate metadata, signed |
| Stable | Supported release | Separate metadata, signed, rollback capable |

## Versioning

Semantic versioning is used. The current version is `0.2.0`, which is the first signed Android release. A major version requires an architecture compatibility review recorded in the release notes.

## Release Automation

The release workflow builds the signed packages when a tag matching `v` followed by the semantic version is pushed, and it can also be started manually with a version input. The workflow runs the repository policy gate, assembles the release variant, verifies every package with the Android build tools, writes checksums and publishes a GitHub release with the packages attached. The signing material is provided through repository secrets and is never stored in the repository.

## Release Checklist

Every release must confirm each item with evidence:

```text
Build passes
Unit tests pass
Network tests pass
Android scaffold validation passes
Security tests pass
Dependency audit passes
License audit passes
Branding scan passes
Emoji scan passes
Comment scan passes
English scan passes
Architecture check passes
Skill integrity verified
Profile migration verified
DNS, DNS over HTTPS and DNS over TLS verified where applicable
Geo, timezone and locale verified
Installer verified where applicable
Uninstaller verified where applicable
Update signature verification verified where applicable
Documentation matches implementation
```

## Evidence Rules

Each checklist item names a command, its exit code and its artifact path. A checklist item without a log reference is not complete.

## Current Release Status

The repository is at version `0.1.0` with the environment core, policy scanners, Android scaffold validation and identity assets complete. Engine builds, packaging and the update system are not executed in this environment and are therefore recorded as not applicable rather than passed.
