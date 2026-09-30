# LA Brow

LA Brow is a browser platform project that pairs a Gecko based browser with a browser scoped environment system. The environment system controls what the browser itself exposes to web content: geographic location, radius based location randomization, timezone surfaces, locale and language negotiation, browser scoped DNS, DNS over HTTPS, DNS over TLS, WebRTC candidate policy and per site environment policies.

The project is organized so that each capability belongs to a named subsystem with an explicit interface, a deterministic failure mode and observable diagnostics.

## What This Repository Contains Today

Executable and tested in this repository:

- Environment resolution pipeline with eleven ordered stages and recorded stage status
- Geo engine with manual, automatic, hybrid and disabled providers
- Radius based coordinate sampling with deterministic seeds and verified containment
- Environment state machine with deterministic transitions
- Timezone resolution using the IANA time zone database, including daylight saving transitions
- Locale and language negotiation with five explicitly separated surfaces
- DNS message encoding and decoding for the record types the resolver returns
- Browser scoped DNS engine with system, DNS over HTTPS and DNS over TLS transports, explicit fallback policy and cache
- Profile storage with schema validation, version migrations, checksum and signature integrity, safe import, export and rollback
- Per site policy engine with documented precedence
- Privacy policy engine expressed as preferences rather than engine duplication
- WebRTC policy presets with a documented limitation statement
- Consistency diagnostics and redacted diagnostic export
- Gecko integration artifact generation for preferences and enterprise policy
- Browser shell model for tabs, navigation, private browsing, permissions and recovery
- Android application scaffold using GeckoView with control center interface, storage layout and resolver configuration
- Policy scanners for emoji, source comments, non English scripts and restricted branding
- Identity system: vector assets for every surface plus raster legibility validation from 16 to 1024 pixels

Scaffolded but not built in this environment:

- The Gecko engine build itself. The measured environment has no Rust, Clang, CMake, Ninja or Android SDK, so a full Gecko and Android build cannot run here. The repository produces the preference artifacts, policy files and integration descriptors that a capable build host consumes. See `docs/architecture/environment-report.md` and `docs/architecture/gecko-integration.md`.

## Quick Start

```bash
python3 tools/agent/bootstrap.sh
python3 -m pytest tests -q
python3 tools/scanners/run_all_scans.py --repo .
python3 -m application.cli environment --url https://example.com --summary
python3 -m application.cli dns --list-profiles
python3 -m application.cli diagnostics --level redacted --out diagnostics-report.json
```

## Engineering Rules In Force

- English only across source, resources, documentation and logs
- No emoji anywhere in the repository
- No traditional source comments; documentation lives in documentation files
- Restricted branding never appears in user facing resources outside permitted about and legal surfaces
- Every external resource is recorded in `docs/licenses/THIRD_PARTY_RESOURCES.md` with license, purpose and integration location
- Every dependency must justify itself; existing Gecko capability and the standard library come first
- No silent operating system DNS modification
- No silent fallback to physical geolocation while virtual mode is active
- No anonymity claims and no fingerprint guarantee claims

All of the above are enforced by executable checks in `tools/scanners/` and by the continuous integration workflow in `ci/`.

## Documentation Map

- `docs/architecture/system-architecture.md`
- `docs/architecture/environment-report.md`
- `docs/architecture/gecko-integration.md`
- `docs/architecture/geo-architecture.md`
- `docs/architecture/network-architecture.md`
- `docs/architecture/dns-architecture.md`
- `docs/architecture/profile-architecture.md`
- `docs/architecture/android-architecture.md`
- `docs/architecture/desktop-architecture.md`
- `docs/security/threat-model.md`
- `docs/testing/test-strategy.md`
- `docs/releases/release-process.md`
- `docs/operations/troubleshooting.md`

## License

MIT. See `LICENSE`. Third party resources are recorded in `docs/licenses/THIRD_PARTY_RESOURCES.md`.
