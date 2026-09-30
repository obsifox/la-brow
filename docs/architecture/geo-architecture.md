# Geo Architecture

## Providers

The geo engine resolves a request through exactly one provider. The provider set is fixed and named:

```text
GeoEngine
    |
    +-- PhysicalProvider
    +-- VirtualProvider
    +-- AutomaticProvider
    +-- HybridProvider
    +-- DisabledProvider
```

| Provider | Source Reported | Behaviour |
| --- | --- | --- |
| Physical | `physical` | Uses a registered operating system bridge; unavailable when no bridge is registered |
| Virtual | `virtual` | Samples a coordinate inside the permitted radius from the profile |
| Automatic | `automatic` | Derives a coarse country level proposal from environment signals |
| Hybrid | `hybrid` | Combines an automatic base with explicit manual overrides |
| Disabled | `disabled` | Refuses resolution with a structured error |

Providers that are not selected for the active mode are constructed lazily, so an unused provider cannot influence a resolution.

## Fix Contract

Every fix reports:

- coordinate with latitude, longitude, accuracy, optional altitude, heading and speed
- source and mode
- confidence between zero and one
- timestamp
- provider identifier
- signal list explaining the decision
- randomization seed when randomization was applied

## Radius Randomization

A location is a center plus a permitted radius, not necessarily a fixed coordinate. Sampling rules:

- Uniform area sampling on the disk, using the square root radial transform, which yields the area uniform distribution rather than a center biased one
- Bounds validation rejecting non numeric, non finite, out of range and non positive values where positive values are required
- Containment verification after sampling, with a strict tolerance
- Deterministic seeds derived by hashing, so a test can reproduce a coordinate exactly

Randomization scopes:

| Scope | Seed Source | Stability |
| --- | --- | --- |
| `none` | Not applicable | The center is returned unchanged |
| `per_query` | Base seed, session, profile, query index | A new coordinate per query |
| `per_session` | Base seed, session, profile | Stable for the session |
| `per_profile` | Base seed, profile | Stable while the profile is active |

## Virtual Mode Rule

When virtual mode is active, the engine never falls back to physical geolocation. A failed resolution raises `PhysicalFallbackForbiddenError` instead of degrading silently. The pipeline additionally reports the matching invariant on every run, and the environment validation stage rejects a profile that disables fallback blocking in manual mode.

## Automatic Detection Honesty

Automatic mode produces a country level proposal with a confidence value and a signal list. The confidence is capped, the accuracy value is coarse by construction, and the fix carries the note that it is not a measurement of the physical position. When no signal is available the provider raises, and the pipeline reports the failure rather than inventing a location.

## Hybrid Transparency

Hybrid mode reports the automatic base, every manual override with the field name, and whether the override conflicts with the detected environment. Manual decisions are never hidden.

## Controlled and Uncontrolled Surfaces

The geo system controls the browser geolocation surface, the timezone surfaces listed in `timezone/gecko_mapping.py`, and the locale surfaces listed in `locale_engine/gecko_mapping.py`. It does not control the operating system clock, other applications, file system timestamps or network routing.

## What This Design Does Not Do

- It does not change the public network address observed by remote services
- It does not claim that automatic detection yields an accurate position
- It does not present consistency diagnostics as an anonymity guarantee
