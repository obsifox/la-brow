# Independent Code Review

Reviewer role: reviewer and security-reviewer lenses per the engineering orchestration skill contracts.
Reviewed artifact set: environment core, specialized engines, tools, tests and Android scaffold at the current working tree.
Evidence base: `pytest tests -q` output, `tools/ci/run_gate.py` report, policy scanner output, architecture check output.

## Summary

The repository builds statically, all tests pass, and every declared policy gate passes. Findings below are grouped by severity. No unresolved HIGH finding blocks the current milestone, because the HIGH finding concerns a future engine build step that does not run in this environment.

## Findings

### R1 HIGH, blocking for the engine build milestone only

Where: `android/app/src/main/java/com/labrow/browser/core/GeckoRuntimeHolder.kt`
Problem: `applyEnvironmentPreferences` uses `runtime.settings.setPref`. The GeckoView Java API exposes preference access differently across versions, and the call is not verified against the pinned artifact because the Android SDK is absent in this environment.
Status: open.
Required action: verify the preference API against the pinned GeckoView version on a build host, or move preference application to the supported configuration path, before claiming any Android build.

### R2 MEDIUM, resolved during review

Where: `environment/core.py` provider construction
Problem: all providers were constructed for every resolution, so an unused provider could fail on a configuration that the active mode does not require. Automatic mode with a profile lacking coordinates failed for this reason.
Status: resolved. Providers are now constructed through deferred factories and only the selected mode is instantiated. Covered by the automatic mode and hybrid mode tests.

### R3 MEDIUM, resolved during review

Where: `policy/engine.py`
Problem: the trace labelled the first writer of a field as an override, which made the precedence record misleading.
Status: resolved. Rules are still matched from most specific to least specific, and merge is applied from least to most specific so the trace records the replacing rule and the replaced value. Covered by the trace test.

### R4 MEDIUM, open, low operational risk

Where: `application/cli.py` geo command
Problem: a loaded profile variable is assigned and not used after the snapshot is produced.
Status: open. Cosmetic. No behavioural effect. Tracked for the next refactor pass.

### R5 LOW, accepted

Where: `MainActivity.togglePrivateMode`
Problem: the private mode toggle re-applies the content tree rather than updating state in place.
Status: accepted for a scaffold. Behaviour is correct and the session is rebuilt, which is the intended semantic. Noted for the production activity implementation.

### R6 LOW, accepted

Where: `.eng/artifacts` skip in `tests/security/test_policy_scanners.py`
Problem: one test skips when scan artifacts do not exist yet.
Status: accepted. The test asserts recorded scan state when the pipeline has been run and skips otherwise, which keeps the unit suite runnable before the first pipeline run.

### R7 LOW, informational

Where: `tools/eng-orchestrator`
Problem: vendored third party skill carrying its own markdown that uses emoji and comment syntax.
Status: accepted and recorded as an explicit policy exemption with a declared modification status of unmodified, pinned to a revision and verified by a per file integrity manifest.

## What Was Checked And Passed

- Virtual mode cannot reach the physical provider: asserted by a boundary test that counts physical bridge calls
- Physical fallback refusal raises a dedicated error type in manual mode
- Resolver configuration file is never written: asserted by a source scan across resolver modules
- Profile identifiers reject traversal and malformed values
- Diagnostic export removes tokens at every level
- Event payloads redact sensitive keys
- Every stage of the resolution pipeline reports a status and halting is explicit
- Policy scanners, license manifest, Android scaffold, architecture direction and skill integrity all pass

## Review Conclusion

Current milestone: PASS with one open HIGH finding that is explicitly out of scope for this environment and is recorded as a precondition for the engine build milestone. The finding is not hidden, not downgraded and not closed without evidence.
