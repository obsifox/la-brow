# Rejected Alternatives

This document records architecturally significant options that were evaluated and rejected, together with the reason. It exists so that future contributors do not repeat the same evaluation without new evidence.

## Timezone data source

Selected: system IANA time zone database accessed through the Python standard library client for the database.

Rejected: bundling a private copy of the time zone database inside the repository. Reason: duplicated update responsibility, larger repository, and no measurable benefit for browser scoped control.

## Automatic geographic detection

Selected: coarse country level proposal derived from timezone, language and network signals with an explicit low confidence value.

Rejected: internet protocol geolocation web services as a default mechanism. Reason: a default that requires sending network metadata to a third party contradicts the data minimization policy, and the accuracy claim would be misleading.

Rejected: any claim that automatic detection identifies the physical position of the user. Reason: the available signals do not support that claim.

## Locale implementation location

Selected: locale implementation in the `locale_engine` package while `locale` remains a resource directory.

Rejected: placing Python source in a directory named `locale`. Reason: the directory name shadows the standard library module of the same name and breaks unrelated tooling.

## DNS over TLS transport

Selected: browser scoped transport implemented on top of the environment core with explicit certificate validation and diagnostics.

Rejected: changing the operating system resolver or a system service. Reason: the product must never modify operating system or router level resolver configuration.

## Fingerprint protection claims

Selected: consistency diagnostics that report mismatches between environment surfaces.

Rejected: presenting the environment system as fingerprint anonymity. Reason: the achievable guarantee is limited to the surfaces the browser controls, and overstatement would be misleading.

## Configuration storage format

Selected: JSON documents with explicit schema version fields, checksum metadata and migration functions.

Rejected: opaque binary configuration blobs. Reason: validation, migration and reviewability are required properties.

## Imported profile handling

Selected: treat imported profiles as untrusted input with size limits, schema validation, migration and explicit activation.

Rejected: applying imported configuration directly at load time. Reason: an invalid or hostile profile must never be silently activated.

## Dependency policy

Selected: reuse existing capabilities first, then upstream implementations, then permissively licensed libraries, and only then custom implementation.

Rejected: introducing convenience dependencies for functionality that the standard library or the browser engine already provides.
