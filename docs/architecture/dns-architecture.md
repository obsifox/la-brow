# DNS Architecture

## Scope

The DNS subsystem provides browser scoped name resolution. It selects a resolver, performs the resolution inside the browser scope, records diagnostics and never modifies the operating system resolver configuration.

## Layers

```text
DnsEngine
   |
   +-- transport selection by resolver profile
   |        |
   |        +-- SystemDnsTransport (read only system resolvers)
   |        +-- DohClient (message based over HTTPS)
   |        +-- DotClient (length prefixed over TLS)
   |
   +-- message codec (dns/wire.py)
   |
   +-- diagnostics (dns/diagnostics.py)
```

## Message Codec

The codec implements the message header, question section, name encoding with label length validation, name decoding with compression pointer support and loop detection, and record decoding for address, name, mail exchange, text, start of authority and service records. Unknown record types are returned as raw payload rather than being silently dropped. Truncation, recursion flags and response codes are exposed. Tests cover each supported record type, pointer loops, truncation, boundary violations and error response codes.

## Resolver Profiles

Resolver profiles are declared in `config/network/dns-providers.yaml` and are bundled into the Android application as a raw resource. Each profile records identifier, display name, protocol, endpoint or hostname, port, bootstrap addresses, TLS verification, timeout, fallback policy and a privacy note.

| Profile | Protocol | Notes |
| --- | --- | --- |
| `system` | system | Reads the operating system resolvers without modifying them |
| `cloudflare-doh` | doh | HTTPS endpoint with bootstrap addresses |
| `quad9-doh` | doh | HTTPS endpoint with bootstrap addresses |
| `cloudflare-dot` | dot | TLS hostname and port 853 |
| `quad9-dot` | dot | TLS hostname and port 853 |

## Fallback Policy

Fallback is explicit and configurable per profile:

| Policy | Behaviour On Failure |
| --- | --- |
| `never` | The failure is reported with no substitution and the note states why |
| `system_on_failure` | The configured secondary profile is used and the result is marked as a fallback with the originating error code |
| `explicit` | Reserved for a caller mediated confirmation flow |

The default in the shipped configuration is `never` plus a documented secondary profile, and the configuration declares that operating system wide changes are forbidden.

## TLS Validation

DNS over TLS and DNS over HTTPS use the platform trust store by default and verify the hostname. A certificate failure is reported as a TLS error with the endpoint and the underlying detail. Tests prove that an untrusted certificate is rejected for both transports and that an unexpected content type or an error status is rejected for the HTTPS transport.

## Diagnostics

`DnsDiagnosticCenter` reports active resolver, protocol, endpoint, connection status, TLS status, latency, last successful query, last error, fallback state, profile source, cache size and whether the system resolver configuration changed.

## Cache

The cache key includes the resolver identifier, the normalized name and the record type. Entry lifetime is the minimum record time to live from the response, with a configurable default. Cache size is bounded and eviction removes the entry with the earliest expiry.

## Operating System Isolation

Two mechanisms keep the isolation observable:

1. The system snapshot hash recorded before and after a session
2. The consistency diagnostic that raises a high severity finding when the hash changes

No code path in this subsystem writes resolver configuration files.
