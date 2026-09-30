# System Architecture

## Purpose

This document defines the subsystem boundaries, dependency direction and observable behaviour of the LA Brow environment platform.

## Layer Model

```text
User interface and control center
        |
Application service and command line interface
        |
Environment core
        |
Specialized engines
        |
Gecko integration surfaces
        |
Operating system
```

The dependency direction is one way. An engine never calls upward into the application layer or the user interface. This is enforced by `tools/agent/architecture_check.py`, which fails when a forbidden import direction appears.

## Subsystems

| Subsystem | Path | Responsibility | Failure Mode |
| --- | --- | --- | --- |
| Environment core | `environment/core.py` | Runs the ordered resolution pipeline and reports stage status | Halts on blocking validation failure and marks remaining stages as SKIPPED |
| Geo engine | `geo/` | Resolves location through exactly one provider per request | Raises a structured error and refuses physical fallback in virtual mode |
| Timezone engine | `timezone/` | Resolves a browser scoped zone, offset and daylight saving state | Rejects an unknown zone identifier |
| Locale engine | `locale_engine/` | Resolves browser locale, language preference and HTTP negotiation | Rejects an invalid language tag |
| DNS engine | `dns/` | Resolves names through one active resolver profile with explicit fallback | Reports failure without substitution when the fallback policy is never |
| DNS over HTTPS | `doh/` | Message based resolution over HTTPS with TLS validation | Rejects an untrusted certificate and an unexpected content type |
| DNS over TLS | `dot/` | Length prefixed resolution over TLS with strict validation | Rejects an untrusted certificate |
| Profile engine | `profiles/` | Stores, validates, migrates, exports, imports and rolls back profiles | Rejects an invalid or hostile profile before activation |
| Policy engine | `policy/` | Resolves per site overrides with deterministic precedence | Unmatched sites fall back to the global scope rule |
| Privacy engine | `privacy/` | Expresses privacy controls as preferences without duplicating the engine | Delegates protection lists and storage implementation to Gecko |
| WebRTC policy | `webrtc/` | Provides named candidate exposure presets | Presets are limited to preference level control |
| Diagnostics | `diagnostics/` | Reports consistency findings and produces redacted exports | Redaction is applied before export, never after |
| Gecko integration | `gecko/` | Generates preferences, policy files and integration descriptors | Reports which upstream surfaces still require patches |
| Browser shell | `browser/shell.py` | Tabs, navigation, private browsing, permissions, recovery | Keeps session state independent from environment resolution |

## Resolution Pipeline

Every environment resolution runs the same ordered stages:

```text
profile_resolution
policy_resolution
environment_validation
geo_resolution
timezone_resolution
locale_resolution
network_resolution
dns_resolution
privacy_policy
gecko_integration
web_content_ready
```

Each stage reports one of `OK`, `FAILED` or `SKIPPED`. A halting stage marks every later stage as `SKIPPED`, which makes the failure position explicit rather than implied. The pipeline is deterministic for the same input, and stage order is asserted by tests.

## Event Model

Structured events are emitted for pipeline start, geo resolution, geo change, timezone change, locale change and failures. Events carry a name, a severity from the documented set, an actor and a payload. Payload keys that look like credentials are redacted before the event is stored.

## Invariants

The pipeline evaluates and reports invariants on every run:

- Virtual mode must not silently fall back to physical geolocation
- Browser scoped DNS never modifies operating system settings
- The environment pipeline does not change public network routing or the observed public address
- Consistency diagnostics are not a fingerprint anonymity guarantee
- Every resolution reports its source and confidence

## State Machine

The environment state machine uses the states `UNKNOWN`, `DETECTING`, `DETECTED`, `MANUAL`, `AUTOMATIC`, `HYBRID`, `CONFLICT`, `ERROR` and `DISABLED`. Transitions are validated, recorded and testable. Rejected transitions raise a structured conflict error.

## What This Architecture Does Not Claim

- It does not virtualize the operating system clock or other applications
- It does not change the public network address
- It does not guarantee anonymity or fingerprint protection
- It does not claim automatic detection identifies a physical position
