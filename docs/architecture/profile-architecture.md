# Profile Architecture

## Model

A profile is a versioned document describing an environment selection. Version two fields:

```yaml
name:
profile_version:
country:
region:
city:
latitude:
longitude:
radius:
accuracy_m:
randomization:
randomization_seed:
block_physical_fallback:
timezone:
locale:
languages:
dns:
doh:
dot:
webrtc_policy:
geolocation_mode:
conflict_detection:
notes:
```

Unknown fields are rejected by default so that a typo cannot silently disable a rule. A caller may opt into forward compatibility explicitly.

## Versioning and Migration

Profiles carry an explicit `profile_version`. Version one to version two migration converts a boolean randomization flag into a named scope, renames the resolver field and converts a boolean DNS over HTTPS flag into a named state. Every migration step is recorded in the applied list returned with the migrated document. A profile newer than the supported version is rejected with a structured version error rather than being partially interpreted.

## Integrity

Every stored profile carries a checksum envelope. Optional signing uses a keyed message authentication code so that a profile can be verified before activation. Tampering is detected and reported as an integrity error. Envelope opening can require a signature, in which case an unsigned profile is refused.

## Storage

```text
var/
  profiles/
    index.json
    <profile-id>.json
    backups/
      <profile-id>.<timestamp>.json
```

Files are written atomically with a temporary file and a rename, and permissions are restricted on creation. Profile identifiers must match a restricted pattern and may not contain traversal sequences.

## Import and Export

Import is treated as untrusted input:

1. Size limit enforcement
2. JSON parsing with a structured parse error
3. Envelope verification when integrity metadata is present
4. Version migration
5. Normalization
6. Strict schema validation
7. Optional dry run that performs no write

Export produces a self describing envelope with the integrity block, the export timestamp and the supported migration path.

## Rollback

Saving over an existing profile first writes a timestamped backup. Rollback restores the most recent backup and reports the restored revision. A rollback without a backup is a structured error rather than a silent no operation.

## Activation Rule

An imported profile is never applied directly. It is validated, migrated and normalized, and only then stored and activated.
