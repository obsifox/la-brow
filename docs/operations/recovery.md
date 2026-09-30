# Recovery Operations

## Failure Catalogue

| Failure | Detection | Recovery |
| --- | --- | --- |
| Invalid profile | Validation stage fails and the pipeline halts | Correct the profile; the previous profile remains active because activation is transactional |
| Corrupted configuration | Checksum mismatch reported as an integrity error | Restore from the timestamped backup |
| DNS failure | Resolution failure reported with the error code | No substitution when the fallback policy is never; switch the profile explicitly |
| DNS over HTTPS failure | TLS or transport error reported | Fix the endpoint or select another profile; no silent downgrade |
| DNS over TLS failure | TLS or transport error reported | Fix the hostname or select another profile |
| Network disconnect | Network state change event | Session snapshot persisted; environment re-evaluation visible in the document |
| Virtual private network change | Network state change event | Automatic and hybrid modes may re-evaluate; manual profiles are not overwritten |
| Engine crash | Crash detected | Session snapshot restored, tab marked as recovered |
| Application restart | Recovery path | Pending session restored from the snapshot |
| Android process recreation | Activity recreation | Instance state provides private mode, control center and pending session |

## Rules

1. Recovery never switches to an unexpected environment
2. Recovery never activates an invalid profile
3. Recovery always preserves the previous known good configuration
4. Every recovery path reports what happened in the environment document and the event log

## Verification

Recovery behaviour is covered by rollback tests, session restore tests, crash recovery tests, invalid profile halting tests and resolver failure tests.
