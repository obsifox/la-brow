# Network Security

## Transport Rules

| Transport | Rule |
| --- | --- |
| DNS over HTTPS | Message content type enforced, status code enforced, transaction identifier matched, certificate verified |
| DNS over TLS | Hostname verified, transaction identifier matched, length prefixed framing enforced |
| System resolver | Read only usage; both UDP and TCP; truncation triggers TCP retry |
| Web content | Cleartext forbidden by Android network security configuration |

## Certificate Handling

The default trust source is the platform trust store. A test proves that a self signed certificate is rejected unless it is explicitly trusted by the caller, which only happens inside tests. Disabling verification is expressible in the profile model and must be explicit, and the default is verification on. The manifest validator and the resolver configuration test assert that shipped encrypted profiles require TLS validation.

## Failure Handling

| Failure | Behaviour |
| --- | --- |
| Timeout | Structured timeout error with endpoint and timeout value |
| Connection refusal | Structured transport error |
| TLS failure | Structured TLS error, no retry without validation |
| Response code error | Resolution failure reported with the response code name |
| Truncated response | TCP retry on the same resolver |
| Fallback policy never | Failure reported, no substitution |

## WebRTC

Presets are documented with their tested dimensions and with the limitation statement that they do not guarantee anonymity and do not change the observed public address.

## Proxy And Virtual Private Network

Proxy environment variables and virtual private network interfaces are detected and reported, never modified. Detection contributes to the network confidence value, which is reported with its notes.

## Operating System Isolation

The resolver configuration file is read and hashed. No code path writes it. The integrity comparison is part of every resolution status and every diagnostic report, and a change raises a high severity consistency finding.
