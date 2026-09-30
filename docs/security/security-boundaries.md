# Security Boundaries

## Boundary List

```text
Browser user interface
Browser controller
Environment core
Specialized engines
Gecko integration surfaces
Operating system
```

## Rules

1. The user interface reads environment state and writes configuration intent. It never drives engine internals directly.
2. The environment core owns resolution. It never writes user interface state.
3. Engines own their domain and expose a typed interface. The geo engine does not own the user interface; the DNS engine does not own the profile engine; the profile engine does not touch operating system networking.
4. Operating system resources are reachable only through a documented boundary. Physical geolocation is reachable only through a registered bridge object, and the provider refuses to act without one.
5. Content processes receive the resolved environment document only. They never read system configuration directly.

## Privileged Actions And Required Permission

| Action | Requires |
| --- | --- |
| Location access | User granted permission plus active environment policy |
| Network inspection | Browser process only |
| Configuration modification | Explicit user action or validated profile activation |
| Profile import | Validation before activation |
| Profile export | User action, integrity metadata included |
| Diagnostic export | Redaction level selection, redacted by default |
| Update installation | Signature verification |

## Enforcement

The engineering skill control plane in `tools/eng-orchestrator/config/permissions.yaml` declares a least privilege matrix per role. The static architecture check in `tools/agent/architecture_check.py` verifies that the documented dependency direction is not violated by the source tree.

## Boundary Failure Behaviour

A boundary violation is a failure, not a warning:

- An unresolved virtual environment raises a forbidden fallback error rather than degrading
- A profile that fails validation is never activated
- A diagnostic export with an unknown level is refused rather than defaulted silently
- A resolver profile without a hostname or endpoint raises at construction time
