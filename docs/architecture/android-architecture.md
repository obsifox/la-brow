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

The engine is GeckoView, pinned to version 130.0.20240904133848 from the Mozilla Maven repository. Session settings enable private mode when requested, tracking protection and media suspension when inactive. Remote debugging is disabled. DNS over HTTPS settings are applied through the runtime settings API when a resolver profile is selected.

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

- Assembling the application requires an Android SDK, a Gradle distribution and network access to the Mozilla Maven repository. None of these exist in the measured environment, so the correct status is validated scaffold.
- The environment document is consumed read only by the control center. Generating it on device requires the environment core to be embedded, which is planned as a follow up task with its own acceptance criteria.

## Validator

`tools/android/validate_scaffold.py` enforces twenty structural checks including required files, minimal permissions, cleartext prohibition, backup exclusion, single activity with launcher and browsable intents, English only user strings with the required notices, adaptive icon layers, absence of source comments in Kotlin files, engine dependency, Compose enablement, release minification, bundled resolver profiles, resolver policy, and the storage directory contract.
