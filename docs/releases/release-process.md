# Release Process

## Channels

| Channel | Purpose | Update Configuration |
| --- | --- | --- |
| Nightly | Continuous integration artifacts | Separate metadata, unsigned development builds are never distributed |
| Development | Feature complete, not verified | Separate metadata |
| Beta | Release candidate verification | Separate metadata, signed |
| Stable | Supported release | Separate metadata, signed, rollback capable |

## Versioning

Semantic versioning is used. The current library and scaffold version is `0.1.0`. A major version requires an architecture compatibility review recorded in the release notes.

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
