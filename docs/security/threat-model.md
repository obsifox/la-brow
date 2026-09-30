# Threat Model

## Method

Assets, adversaries, attack surfaces and mitigations are listed. Each mitigation names the mechanism that implements it and the evidence that verifies it. Claims without evidence are marked as planned.

## Assets

| Asset | Description |
| --- | --- |
| Environment configuration | Profiles, resolver selection, per site policies |
| Diagnostic exports | Environment state reports produced for support |
| Resolver traffic | Name queries and their metadata |
| Session state | Tabs, navigation history, private browsing state |
| Integrity of the browser binary | The code that enforces every rule above |

## Adversaries

| Adversary | Capability |
| --- | --- |
| Malicious website | Attempts to read environment surfaces, fingerprint, or abuse permissions |
| Malicious extension | Attempts to read or modify environment state |
| Compromised resolver | Returns forged answers or observes queries |
| Network observer | Observes plaintext resolution and connection metadata |
| Local attacker | Reads configuration files or modifies them |
| Malicious profile | Supplies a crafted configuration to change behaviour or escape validation |
| Compromised dependency | Injects code through build or runtime dependencies |
| Update attacker | Substitutes an update artifact |

## Mitigations

| Threat | Mitigation | Evidence |
| --- | --- | --- |
| Malicious website reading physical location | Virtual mode overrides the geolocation surface and physical fallback is refused | `geo/engine.py`, pipeline invariant test |
| Malicious website fingerprinting through inconsistencies | Consistency diagnostics report mismatches so the operator can align surfaces | `diagnostics/consistency.py`, unit tests |
| Compromised resolver | TLS validation with hostname verification and no silent downgrade | Transport tests rejecting untrusted certificates |
| Network observer reading queries | DNS over TLS and DNS over HTTPS transports with explicit selection and visible diagnostics | `doh/client.py`, `dot/client.py`, transport tests |
| Local attacker reading configuration | Restricted file permissions on profile writes, explicit storage layout, backup exclusion on Android | `profiles/store.py`, Android validator backup check |
| Malicious profile | Untrusted input handling: size limit, schema validation, migration, unknown field rejection, optional signature, dry run | Profile tests including traversal and oversized payload cases |
| Silent environment change | Manual profiles are never overwritten by network changes; automatic decisions are always reported | Pipeline reporting, consistency diagnostics |
| Operating system resolver modification | No write path exists; integrity hash comparison raises a high severity finding | `dns/engine.py` integrity check, consistency test |
| Dependency compromise | Recorded manifest with license, source, version and pinned revision for vendored code; integrity manifest with per file hashes | `docs/licenses/THIRD_PARTY_RESOURCES.md`, skill verification tool |
| Update substitution | Signature requirement and refusal of unsigned artifacts | Planned at packaging stage, requirement recorded in `config/build/targets.yaml` |
| Secret exposure through logs or diagnostics | Redaction of sensitive keys in events and in diagnostic exports at all levels | Event and redaction tests |

## Residual Risk

- Automatic detection is coarse and can be wrong; it is reported with confidence and notes rather than presented as a fact
- WebRTC presets reduce candidate exposure but do not hide the public address
- Consistency diagnostics reduce observable contradictions but cannot guarantee fingerprint uniformity
- Engine level patches required for timezone and geolocation overrides are not implemented in this repository

## Out Of Scope

- Circumventing service restrictions, sanctions, licensing or access controls
- Any behaviour that advertises anonymity guarantees
