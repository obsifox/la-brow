# Android Architecture

## Position In The System

The Android application is the same conceptual architecture as the desktop shell. The environment core, profile engine, DNS engine and diagnostics are shared concepts; the platform integration layer differs.

```text
MainActivity
   |
   +-- browser surface (GeckoView)
   +-- control center (Compose)
   |
Environment and storage layer
   |
   +-- EnvironmentRepository (environment document, network state, session)
   +-- ProfileRepository (validation, import, export)
   +-- DnsRepository (bundled resolver profiles, active resolver)
   +-- StorageLayout (directory contract)
   |
GeckoRuntimeHolder
   |
GeckoView runtime and session
```

## Engine Integration

The engine is GeckoView, pinned to version 153.0.20260810162159 from the Mozilla Maven repository. Session settings enable private mode when requested, tracking protection and media suspension when inactive. Remote debugging is disabled. Browser scoped DNS over HTTPS uses the trusted recursive resolver mode and trusted recursive resolver URI runtime settings when a resolver profile is selected, and the trusted recursive resolver is switched off when the selected profile is the system resolver. Arbitrary browser preferences are applied through the Gecko preference controller on the user branch, which is the supported replacement for direct preference writes.

## Storage Contract

```text
files/
  profiles/
    index.json
    <profile-id>.json
  settings/
    settings.json
    environment.json
    session.json
  diagnostics/
cache/
  cache/
```

Configuration is separated from cache. The cache directory is a cache directory by platform definition and may be reclaimed by the system without affecting configuration. Backup and device transfer explicitly exclude profiles, settings and databases so that a configuration is never silently copied to another device or to a cloud backup.

## Permissions

The manifest declares only `INTERNET` and `ACCESS_NETWORK_STATE`. The scaffold validator fails the build when any other permission appears. Cleartext traffic is forbidden globally through the network security configuration, with explicit domain entries only for the documented resolver endpoints and with system trust anchors.

## Lifecycle And Recovery

- Session snapshot is written when the activity saves instance state and when the network becomes available or is lost
- Activity recreation restores the pending session
- Configuration changes are declared so that the engine view is not recreated on rotation
- The private mode toggle rebuilds the session rather than mutating a live session

## What Remains

- Assembly runs on a host with JDK 17, the Gradle wrapper pinned to 8.14.3, Android Gradle plugin 8.13.2 and Android platform 36 with build tools 36. The continuous integration workflow installs exactly those components and publishes the debug packages as build artifacts. The debug output is split per application binary interface for arm64-v8a, armeabi-v7a and x86_64, and a universal package is produced as well.
- The environment document is consumed read only by the control center. Generating it on device requires the environment core to be embedded, which is planned as a follow up task with its own acceptance criteria.

## Validator

The merged manifest requests internet and network state from the application itself. The engine artifact contributes wake lock, audio settings and high sampling rate sensor permissions during manifest merging, which is recorded here so the merged permission set is never mistaken for an application decision.

`tools/android/validate_scaffold.py` enforces thirty-eight structural checks including required files, minimal permissions, cleartext prohibition, backup exclusion, single activity with launcher and browsable intents, English only user strings with the required notices, adaptive icon layers, absence of source comments in Kotlin files, engine dependency, Compose enablement, release minification, bundled resolver profiles, resolver policy, and the storage directory contract.

## Application Interface Client

The Android application does not resolve the environment on the device. It requests an environment snapshot from the application server and stores the result locally so the mobile control center and the desktop control center observe the same values.

```text
MainActivity
   |
SyncController
   |
ApiClient (connect timeout 8000 ms, read timeout 20000 ms)
   |
GET /api/environment with url, profile, resolver, privacy and private parameters
   |
EnvironmentMapper -> EnvironmentDocument
   |
EnvironmentRepository (files/settings/environment.json)
```

The default server address is the emulator loopback alias for the host machine followed by port 8000. The address can be replaced at runtime; the value is stored in files/settings/app.json under the key api_base_url.

Cleartext traffic is permitted only in the debug variant, and only for the development hosts 10.0.2.2, 127.0.0.1 and localhost. The release variant keeps cleartext disabled and trusts system certificate authorities only.

Profile editing uses PUT and DELETE on the profile route, validation uses POST on the validation route, and resolver probing uses POST on the probe route. Diagnostics export requests GET /api/diagnostics with an explicit level and writes the returned report to files/diagnostics/diagnostics-<level>.json.

## Interface Contract Verification

tests/android/test_client_contract.py reads the Kotlin sources for the endpoints the client calls and the payload fields the mapper reads, then exercises those endpoints against an in-process application server. The suite fails when the client calls an endpoint the server does not expose, when a field the mapper reads is absent from the payload, or when the storage repository reads a key that the sync layer never writes. The Android client therefore stays verifiable without an Android build toolchain.

## Build Host Requirements

A build host needs JDK 17 and Android SDK platform 36 with build tools 36. The Gradle 8.14.3 distribution is pinned by the wrapper in android/gradle/wrapper, so `./gradlew assembleDebug` reproduces the same build everywhere. The GeckoView artifact is resolved from the Mozilla Maven repository. android/build-debug.sh checks the toolchain and reports exactly what is missing before it runs a debug assembly.

## Design System

The interface is dark first with a gradient and gaming treatment. The design system lives in the theme package and is applied by every screen.

| Element | Implementation |
| --- | --- |
| backdrop | drifting radial gradients over a masked grid drawn on a canvas |
| panels | gradient frame, glass body and a per group accent colour |
| status chips | tone colour with a paired indicator dot for pipeline and consistency states |
| scores | ring gauges for location confidence and add-on compatibility |
| navigation | bottom rail of destinations, the selected item carries the active theme gradient |
| theme source | the product palette by default, replaced by a translated desktop theme when one is active |

Every colour and gradient is derived from the identity palette, so a translated desktop theme changes the shell without touching screen code.

## Desktop Add-On Surfaces

The add-on screen shows the runtime matrix, inspects a pasted desktop manifest, requires the acknowledgement toggle before an installation is recorded, lists recorded add-ons with their compatibility level and signature state, and activates a recorded theme.

| Surface | Behaviour |
| --- | --- |
| inspect | compatibility report with per surface levels and the mandatory notice |
| install | refused until the notice is acknowledged, prohibited permissions are refused regardless |
| registry | recorded add-ons with level, score, signature state and the acknowledged notice text |
| theme | activation stores the translated gradient and applies it across the shell |
| offline | the last active theme is persisted so the shell keeps its gradient without the server |
