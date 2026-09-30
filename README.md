# LA Brow

A browser platform with browser scoped environment virtualization: virtual location, timezone, locale, resolver and policy are resolved by one deterministic pipeline and shared by every client. The desktop control center, the web client and the Android application all read the same interface.

```text
client surface          interface                engine core
  web control center  ->  GET /api/environment  ->  environment pipeline
  android application ->  GET /api/profiles     ->  profile engine and store
  command line tool   ->  POST /api/dns/probe   ->  resolver engine
                          GET /api/extensions   ->  desktop add-on compatibility
```

## What It Does

| Area | Behaviour |
| --- | --- |
| Location | virtual mode only, radius bounded sampling, seeded and reproducible, never falls back to the device provider |
| Timezone | browser scoped, applied to JavaScript and formatting surfaces, operating system clock untouched |
| Locale | browser locale, language preference, HTTP preference and JavaScript surface resolved separately |
| Resolver | browser scoped DNS over HTTPS and DNS over TLS, system resolver configuration read and hashed, never written |
| Policy | site scoped overrides with origin over subdomain over domain over browsing mode over global precedence |
| Privacy | presets, per surface tri state controls and WebRTC policies with an explicit limitation statement |
| Diagnostics | redaction levels, consistency findings across surfaces and structured pipeline events |
| Add-ons | desktop Firefox theme manifests translated into the application gradient, with a compatibility report and a required notice before installation |

## Desktop Add-On Compatibility

Desktop themes are translated, not emulated:

| Input | Translation |
| --- | --- |
| `theme.colors.frame`, `toolbar`, `tab_selected` | gradient stops of the application shell |
| `theme.colors.button_background_hover` | glow colour behind interactive elements |
| `theme.properties` | colour scheme hints for content surfaces |
| `theme.images.theme_frame` | reported as pending because the packaged theme is required |

Sections and permissions are scored against a reviewable matrix. Unsupported surfaces are refused, partially supported surfaces are reported, and the install flow stops until the user confirms this notice:

> This add-on targets desktop Firefox. Parts of it may not display or behave correctly in the mobile application, and the theme or interface changes it declares are applied on a best effort basis.

## Design Language

The interface is dark first with a gaming gradient system: a drifting backdrop over a grid, gradient framed panels, neon status chips, ring gauges for confidence and compatibility scores, and a bottom rail whose selected item carries the active theme gradient. The palette derives from the identity system and is replaced by the active theme when a desktop theme is installed.

| Token | Value |
| --- | --- |
| void | #05060A |
| obsidian | #0B0C0E |
| neon red | #FF2D3F |
| neon violet | #A855F7 |
| neon cyan | #22D3EE |

## Quick Start

```bash
python3 -m api.server --host 0.0.0.0 --port 8000 --repo .
```

| Surface | Address |
| --- | --- |
| web control center | the server root, six tabs including Add-ons |
| interface | /api/health, /api/environment, /api/profiles, /api/dns/probe, /api/diagnostics, /api/extensions, /api/themes, /api/compat/firefox-desktop |
| command line | `python3 -m application.cli --help` |

## Android Application

| Item | Value |
| --- | --- |
| package | com.labrow.browser |
| engine | GeckoView 153.0.20260810162159 |
| screens | Browser, Environment, Add-ons, Network, Profiles, Settings |
| server default | the emulator loopback alias for the host machine on port 8000 |
| build | `gradle --no-daemon assembleDebug` with JDK 17 and the Android platform 35 |

The debug package is assembled by the `android-build` workflow and published as a build artifact on every change that touches the Android tree. The release variant keeps cleartext traffic disabled and trusts system certificate authorities only.

## Verification

| Suite | Coverage |
| --- | --- |
| unit | environment pipeline, profiles, resolver engine, privacy, diagnostics, add-on compatibility and theme translation |
| interface | every endpoint against a live in-process server |
| android contract | endpoints and payload fields parsed from the Kotlin sources and exercised against the live server |
| network | resolver transports, truncation handling and certificate validation against a local test kit |
| policy | comment, emoji, english and branding scanners plus the license manifest |

The pipeline fails on any policy violation, on a missing license record, on a silent location fallback and on any attempt to modify operating system level resolver settings.

## Repository Layout

```text
api/         interface server and route handlers
ui/          web control center
extensions/  desktop add-on and theme compatibility layer
environment/ deterministic pipeline
geo/ timezone/ locale_engine/ dns/ doh/ dot/ privacy/ webrtc/ profiles/ policy/ diagnostics/
android/     Android application, gradient design system and add-on surfaces
config/      matrix, policy, resolver and browser configuration
docs/        architecture, security, testing, operations and license records
tools/       scanners, validators, identity generator and the engineering control plane
tests/       unit, interface, network, security, integration and android contract suites
```

## Statements

Environment controls do not guarantee anonymity and do not change the public address observed by websites. Resolver configuration never modifies device or network settings. While virtual location mode is active the browser never falls back to the device location provider. Timezone control covers JavaScript and formatting surfaces inside the browser only.

## License

Released under the MIT license. Third party resources are recorded in `docs/licenses/THIRD_PARTY_RESOURCES.md`.
