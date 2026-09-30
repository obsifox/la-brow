# Security Test Matrix

| Case | Expected |
| --- | --- |
| Emoji scan | Repository free of unauthorized emoji, exemptions recorded |
| Comment scan | No source comments outside declared exemptions |
| English scan | No unexpected non English scripts |
| Branding scan | Restricted identifiers absent from user facing resources |
| License manifest | Every resource recorded with an accepted license and an existing integration location |
| Android scaffold | Minimal permissions, cleartext forbidden, backup excluded, no source comments |
| Skill integrity | Vendored engineering skill matches its pinned revision and file manifest |
| Architecture direction | No forbidden import direction in engine sources |
| Untrusted profile | Traversal, oversized, malformed and unsigned cases refused |
| Redaction | Tokens removed at all levels, addresses masked, coordinates rounded or removed |
| Event payloads | Sensitive keys redacted before storage |
| Operating system isolation | Resolver configuration unchanged after a session |
| Virtual fallback | Physical fallback refused in virtual mode |

Executed by the scanners, the validators and the unit and network suites. Continuous integration runs all of them and fails on any violation.
