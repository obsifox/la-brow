# Profile Security

## Threat

A profile is a configuration document that can change location, resolver, privacy and WebRTC behaviour. Imported profiles therefore represent a configuration injection surface.

## Controls

| Control | Implementation |
| --- | --- |
| Size limit | Import refuses payloads above the documented maximum |
| Parse safety | Structured JSON parse errors, no code execution, no expression evaluation |
| Integrity | Checksum envelope, optional keyed signature, tamper detection |
| Signature policy | Signature requirement is a parameter; a required signature rejects unsigned input |
| Version discipline | Unknown or newer versions are rejected with a structured error |
| Schema strictness | Unknown fields rejected by default; type, range and enumeration validation |
| Path safety | Profile identifiers restricted by pattern; traversal sequences refused |
| Atomic write | Temporary file plus rename with restricted permissions |
| Backup before overwrite | Timestamped backup; rollback restores the last revision |
| Activation gate | Imported profiles are validated and migrated before activation |

## Validation Coverage

Validated fields include coordinate ranges, coordinate pairing, radius bounds, accuracy positivity, timezone identifier validity, language tag validity, language list validity, geolocation mode enumeration, randomization scope enumeration, WebRTC policy enumeration and seed type. Tests cover each rejection path.

## Residual Risk

- A profile that passes validation can still describe a contradictory environment. This is reported by consistency diagnostics rather than blocked, because a deliberate mismatch is a legitimate testing scenario.
- Signing keys are supplied by the operator. Key management is outside the scope of the profile store.
