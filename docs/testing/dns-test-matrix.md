# DNS Test Matrix

| Case | Setup | Expected |
| --- | --- | --- |
| Message encoding | Name with labels | Length prefixed labels, trailing root label |
| Long label | Label above sixty three bytes | Encoding error |
| Compression pointer | Pointer to earlier name | Name resolved, position reported |
| Pointer loop | Self referencing pointer | Decoding error |
| Address records | IPv4 and IPv6 payloads | Address values in canonical text form |
| Name records | Name, canonical name, pointer | Target names reported |
| Mail exchange | Preference with exchange name | Structured value |
| Text records | Character strings | String list |
| Start of authority | Authority payload | Structured fields |
| Truncation flag | Truncated header | Flag exposed |
| Error response code | Non zero response code | Named code exposed |
| System resolver query | Local UDP server | Address returned, endpoint reported |
| UDP truncation | Truncated UDP plus TCP server | TCP retry returns full answer |
| Timeout | Silent server | Structured timeout error |
| Closed port | Stopped server | Timeout error on the resolver attempt |
| DNS over TLS success | Local TLS server with trusted certificate | Address returned, TLS verified |
| DNS over TLS untrusted | Untrusted certificate | TLS error |
| DNS over HTTPS success | Local HTTPS server | Address returned |
| DNS over HTTPS content type | Wrong content type | Transport error |
| DNS over HTTPS status | Error status | Transport error |
| Fallback never | Primary failure | Failure reported, no substitution |
| Fallback configured | Primary failure with system secondary | Fallback used and marked |
| Cache | Repeated identical query | Cache hit, single upstream call |
| Cache bypass | Repeated query without cache | Second upstream call |
| Resolver configuration | Shipped configuration file | Profiles loaded, TLS required, no operating system wide changes |
| Operating system integrity | Snapshot before and after | Unchanged, statement recorded |

Executed by `tests/unit/test_dns_wire.py`, `tests/unit/test_dns_engine.py`, `tests/network/test_system_transport.py`, `tests/network/test_dot_and_doh_clients.py` and `tests/network/test_resolver_configuration.py`.
