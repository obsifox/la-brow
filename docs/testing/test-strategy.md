# Test Strategy

## Layers

| Layer | Location | Purpose |
| --- | --- | --- |
| Unit | `tests/unit/` | Value objects, engines, validation, redaction and policy resolution |
| Network | `tests/network/` | Real sockets against local DNS, TLS and HTTPS test servers |
| Android | `tests/android/` | Structural validation of the Android scaffold |
| Security | `tests/security/` | Policy scanners and boundary checks |
| Integration | `tests/integration/` | End to end pipeline and command line behaviour |

## Principles

1. No test may pass without evidence. A test either asserts a measured property or fails.
2. Network behaviour is tested against local servers rather than public infrastructure, so the suite is deterministic and offline capable.
3. Time dependent behaviour is tested by supplying an explicit moment rather than reading the clock.
4. Random behaviour is tested by seeding and by verifying containment, not by asserting a specific coordinate.
5. Policy rules are tested as executable checks, so a violation fails the build.

## Network Test Infrastructure

`tests/network/dns_testkit.py` provides:

- A UDP DNS server with configurable truncation and a silent mode for timeout tests
- A TCP DNS server with length prefixed framing
- A TLS wrapper for DNS over TLS with generated certificates
- An HTTPS server implementing message based DNS over HTTPS with configurable content type and status
- Certificate generation through the system OpenSSL command line tool

## Determinism

The suite uses no external network access. The pipeline is exercised with detection disabled where determinism is required and with detection enabled where signal handling is under test.

## Coverage Intent

Every documented rule has a corresponding executable check:

| Rule | Check |
| --- | --- |
| No emoji | `tools/scanners/emoji_scan.py` |
| No source comments | `tools/scanners/comment_scan.py` |
| English only | `tools/scanners/english_scan.py` |
| Restricted branding | `tools/scanners/branding_scan.py` |
| Declared resources and licenses | `tools/license/verify_manifest.py` |
| Android structure | `tools/android/validate_scaffold.py` |
| Engine skill integrity | `tools/agent/verify_skill.py` |
| Architecture direction | `tools/agent/architecture_check.py` |
