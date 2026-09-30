# Network Architecture

## Scope

The network subsystem observes network state, feeds detection signals to the geo engine, and hosts the resolver transports. It never modifies operating system network settings.

## Observation Surfaces

`network/detection.py` collects:

- interface list with addresses and state flags
- default route interface
- proxy related environment variables
- system resolver addresses read from the resolver configuration file
- virtual private network indicators from interface naming and connection managers
- optional reachability probes for plain DNS, HTTPS and DNS over TLS ports

Resolver configuration is read only. The file is opened for reading, hashed for the integrity record and never written.

## Confidence Model

Detection produces a confidence value from the collected signals together with a note list. The notes and the confidence are carried into the environment document, so a user can see exactly which evidence supported an automatic decision. Confidence is intentionally low; it is a transparency mechanism, not a claim of accuracy.

## Integrity Check

The DNS engine records a hash of the resolver configuration before and after the browser session. `integrity_check()` reports whether the file changed, and the consistency diagnostics raise a high severity finding when it did. This turns the no operating system modification rule into an observable property rather than a promise.

## Network State Changes

The Android application registers a default network callback and persists its session snapshot when the network becomes available or is lost. On desktop, the environment core is designed to be re-run on a network change event; the event names reserved for this are `network.changed`, `vpn.state_changed` and `dns.changed`.

Manual profiles are not overwritten by network state changes. Only automatic and hybrid modes may re-evaluate their automatic portion, and the resulting change is visible in the environment document.

## WebRTC

WebRTC policy is expressed as preference presets:

| Policy | Intent |
| --- | --- |
| `default` | Engine default behaviour |
| `privacy_enhanced` | Suppress host candidates and prefer a single default address |
| `disable_local_candidates` | Relay only candidates |
| `custom` | Caller supplied preference map |

The tested dimensions are STUN, TURN, IPv4, IPv6, proxy, virtual private network and DNS combinations as listed in `webrtc/policy.py`. The limitation statement is part of the policy description and states that these presets do not guarantee network anonymity and do not change the public address observed by remote peers.

## Proxy Interaction

Proxy configuration is detected and reported. It is not modified. The environment document records whether proxy related environment variables were present when the environment was resolved.
