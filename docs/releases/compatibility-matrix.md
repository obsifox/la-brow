# Compatibility Matrix

## Platform Targets

| Target | Status | Notes |
| --- | --- | --- |
| Linux x86_64 | scaffolded, not built | Requires the engine toolchain |
| Windows x86_64 | scaffolded, not built | Requires the engine toolchain |
| macOS universal | scaffolded, not built | Requires the engine toolchain |
| Android arm64-v8a | scaffolded, not built | Requires Android SDK and Gradle |
| Android x86_64 | scaffolded, not built | Requires Android SDK and Gradle |

## Library Compatibility

| Runtime | Verified Version | Notes |
| --- | --- | --- |
| Python | 3.13.14 | Tests and environment core executed in this environment |
| IANA time zone database | System provided | Daylight saving transitions verified for a northern and an eastern hemisphere zone |

## Engine Compatibility

| Component | Version | Status |
| --- | --- | --- |
| GeckoView | 153.0.20260810162159 | Dependency declared and scaffold validated; application not assembled |
| Gecko platform source | to be pinned | Not fetched in this environment |

## Statement Discipline

A compatibility claim requires a passing build and a passing test run for that target. Until then the status remains scaffolded and no support statement is made.
