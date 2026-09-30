# Diagnostics Operations

## Diagnostic Center

The DNS diagnostic center reports active resolver, protocol, endpoint, connection status, TLS status, latency, last successful query, last error, fallback state, profile source, cache size and operating system isolation status.

## Environment Diagnostics

`diagnostics/consistency.py` reports findings across location, timezone, locale, resolver and operating system surfaces. Each finding carries an identifier, a severity, an affected surface list and a suggestion. The highest severity is reported with the status.

## Export Levels

| Level | Coordinates | Addresses | Hostnames | Token Values |
| --- | --- | --- | --- | --- |
| `full` | Exact | Exact | Exact | Removed |
| `redacted` | Rounded | Masked | Exact | Removed |
| `minimal` | Removed | Masked | Removed | Removed |

Redacted is the default. Token values are removed at every level, including the full level, because the export contract states that authentication material is never exported.

## Command Line Usage

```bash
python3 -m application.cli diagnostics --level redacted --out diagnostics-report.json
python3 -m application.cli dns --resolver cloudflare-doh --name example.com --type A
python3 -m application.cli environment --url https://example.com --summary
```

## Interpreting Findings

| Finding | Meaning | Suggested Action |
| --- | --- | --- |
| `timezone-location-mismatch` | The timezone zone is not commonly used in the selected country | Align the profile or document the intentional mismatch |
| `locale-region-mismatch` | Browser locale region differs from the selected country | Review language preferences |
| `resolver-mode-declared-but-not-active` | The profile declares an encrypted resolver while the active resolver is not encrypted | Activate the declared resolver or correct the profile |
| `system-resolver-modified` | The operating system resolver configuration changed during the session | Restore the configuration and investigate |
| `coordinate-country-distance` | The coordinate is far from the declared country centroid | Confirm the intended radius and country |
