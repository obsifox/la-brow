# Update Security

## Requirements

1. Artifacts are signed. An unsigned artifact is never installed.
2. Verification happens before installation, not after.
3. The verification key is pinned in the application and not fetched over the same channel as the artifact.
4. Update metadata is integrity protected.
5. Rollback is available when installation or the first launch fails.
6. Update channels are separate: nightly, development, beta and stable, each with its own metadata.

## Status

The requirements above are recorded in `config/build/targets.yaml` and are binding for the release process. Implementation is planned with the packaging stage, because it requires the signed artifact pipeline that does not exist in this environment.

## Evidence Required Before A Release

- Signed artifact hash recorded in the release manifest
- Verification log showing signature validation succeeded
- A negative test showing an unsigned or modified artifact is refused
- A rollback test showing the previous version can be restored
