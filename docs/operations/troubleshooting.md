# Troubleshooting

## The environment reports `FAILED`

Read the stage list. The first `FAILED` stage is the cause and every later stage is `SKIPPED`. A failing `profile_resolution` stage means validation rejected the profile and the validation problems are attached to the stage output.

## The location is far from the expected city

The radius is the permitted area, not a fixed point. Check the reported sampled distance in the fix notes, and set the randomization scope to `none` when a fixed coordinate is required for a test.

## Automatic mode reports a low confidence or fails

Automatic mode derives a country level proposal from coarse signals and refuses to invent a location when no signal is available. Supply a timezone or locale hint, or switch to manual or hybrid mode.

## The resolver is not the one that was declared

Check the diagnostic center: `resolver_protocol`, `endpoint` and `profile_source`. If the profile declared an encrypted resolver while the active protocol is not encrypted, the consistency diagnostic raises a high severity finding.

## Resolution fails and no fallback happened

The fallback policy is explicit. With `never`, a failure is reported rather than substituted. Select a profile whose policy allows a fallback and confirm that a secondary profile is configured.

## The scanner reports a comment or a branding violation

See `config/engineering/code-style.yaml`. Every exemption carries an identifier, a path pattern, an affected scanner list, a reason and a modification status. An exemption is a policy decision and must be recorded there rather than bypassed by editing the scanner.

## The skill verification fails

Run `python3 tools/agent/verify_skill.py --repo .`. The tool reports missing files and per file hash mismatches against the integrity manifest. Reinstall from the pinned revision with `--install` and regenerate the manifest.

## The architecture check fails

The check reports missing documents, missing modules and forbidden dependency directions. A direction violation means an engine is importing upward; fix the dependency rather than the check.
