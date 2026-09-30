# Gecko Integration

## Scope

This document records how the environment system integrates with a Gecko based browser, which surfaces are preference controllable, which surfaces require patches, and what the build status of the engine is in this repository.

## Build Status

`scaffolded-not-built`.

The measured engineering environment does not provide the Gecko build prerequisites. `docs/architecture/environment-report.md` records the measurements: no Rust toolchain, no Clang, no CMake, no Ninja, no Android SDK. Consequently this repository produces the artifacts a Gecko build consumes and documents the patch surfaces, rather than claiming a built engine.

## Integration Artifacts

`gecko/integration.py` produces three artifacts per resolution:

1. A preference map, ordered deterministically by preference group prefix
2. A `user_pref` style rendering of that map
3. An enterprise policy document carrying the DNS over HTTPS block when a DNS over HTTPS resolver profile is active

The rendering path is tested: preferences are sorted deterministically, booleans and numbers render without quoting, and the policy document omits the resolver block when no endpoint is configured.

## Preference Controllable Surfaces

| Capability | Mechanism | Notes |
| --- | --- | --- |
| HTTP language negotiation | `intl.accept_languages` | Fully preference based |
| Requested locale | `intl.locale.requested` | Fully preference based |
| Application locale | `general.useragent.locale` | Fully preference based |
| Tracking protection | `privacy.trackingprotection.enabled` | Existing engine feature toggled by preference |
| Fingerprinting resistance | `privacy.resistFingerprinting` | Existing engine feature toggled by preference |
| Cookie behaviour | `network.cookie.cookieBehavior` | Existing engine feature toggled by preference |
| Referrer behaviour | `network.http.referer.XOriginPolicy` | Existing engine feature toggled by preference |
| HTTPS only mode | `dom.security.https_only_mode` | Existing engine feature toggled by preference |
| WebRTC candidate policy | `media.peerconnection.*` | Preference presets with a documented limitation statement |
| DNS over HTTPS selection | Enterprise policy `DNSOverHTTPS` | Resolver selection without modifying the operating system |
| Environment metadata | `environment.*` | Project namespace carrying active environment state for diagnostics |

## Surfaces That Require Patches

| Surface | Reason | Planned Approach |
| --- | --- | --- |
| Geolocation provider | Upstream resolves coordinates through the operating system provider | Implement an `nsIGeolocationProvider` replacement that returns the resolved virtual fix and refuses physical fallback in virtual mode |
| Timezone surfaces | `Date.getTimezoneOffset` and `Intl` resolved options are not preference controllable | Add an engine level override hook applied to content processes only |
| JavaScript locale surfaces | Available partially through preferences | Reuse the same override path as the timezone surfaces |
| Environment diagnostics channel | No upstream channel exists | Expose the environment document through a privileged internal interface, never through content accessible APIs |

Every patch surface listed here is registered in `gecko/integration.py` so that the plan and the implementation cannot silently diverge.

## Process Architecture Expectations

The Gecko process model separates the browser chrome process from content processes. The environment system is designed around this boundary:

- Resolution happens in the browser process
- Only the resolved environment document reaches content processes
- Content processes never read operating system location, resolver configuration or network state directly
- Diagnostics reads flow back through the browser process and are redacted before export

## Verification Requirements Before Any Build Claim

A build claim requires the following evidence, none of which exists in this environment:

1. A pinned engine revision recorded in the repository
2. A recorded toolchain inventory from the build host
3. A successful build log with exit code zero
4. A preference artifact diff proving the generated documents were applied
5. Test evidence for geolocation override, timezone override and resolver selection
6. A reproducible build record following `docs/releases/reproducible-builds.md`
