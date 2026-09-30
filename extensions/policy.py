"""Install policy for desktop Firefox themes and extensions."""

from __future__ import annotations

from pathlib import Path

import yaml

from extensions.manifest import ManifestError, WebExtensionManifest, parse_manifest

POLICY_PATH = Path("config/compat/install-policy.yaml")


def load_install_policy(repo: Path) -> dict:
    path = repo / POLICY_PATH
    if not path.is_file():
        raise ManifestError("install policy is missing", path=str(path))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _deny(code: str, message: str, **context: object) -> dict:
    return {"allowed": False, "code": code, "message": message, "context": dict(context), "requires_acknowledgement": False}


def evaluate_install(repo: Path, payload: dict, acknowledged: bool = False) -> dict:
    policy = load_install_policy(repo)
    limits = policy.get("limits", {})
    try:
        manifest = parse_manifest(payload)
    except ManifestError as error:
        return _deny(error.code, error.message, **error.context)
    raw_size = len(manifest.canonical_json().encode("utf-8"))
    if raw_size > int(limits.get("max_manifest_bytes", 262144)):
        return _deny("manifest_too_large", "the manifest exceeds the accepted size", bytes=raw_size)
    if len(manifest.name) > int(limits.get("max_name_length", 128)):
        return _deny("manifest_name_too_long", "the manifest name exceeds the accepted length")
    permissions = manifest.declared_permissions()
    if len(permissions) > int(limits.get("max_permissions", 64)):
        return _deny("manifest_permissions_too_many", "the manifest declares too many permissions", count=len(permissions))
    if manifest.manifest_version not in [int(value) for value in policy.get("allowed_manifest_versions", [2, 3])]:
        return _deny("manifest_version_refused", "the manifest version is not accepted", value=manifest.manifest_version)
    refused_permissions = [permission for permission in permissions if permission in policy.get("prohibited_permissions", [])]
    if refused_permissions:
        return _deny(
            "prohibited_permission",
            "the add-on requests a permission that the product refuses",
            permissions=refused_permissions,
        )
    refused_sections = [section for section in manifest.declared_sections if section in policy.get("prohibited_sections", [])]
    if refused_sections:
        return _deny(
            "prohibited_section",
            "the add-on declares a section that the product refuses",
            sections=refused_sections,
        )
    acknowledgement = policy.get("acknowledgement", {})
    if acknowledgement.get("required", True) and not acknowledged:
        return {
            "allowed": False,
            "code": "notice_not_acknowledged",
            "message": acknowledgement.get(
                "message",
                "the user must confirm the compatibility notice before an installation is recorded",
            ),
            "context": {"field": acknowledgement.get("field", "acknowledged")},
            "requires_acknowledgement": True,
        }
    return {
        "allowed": True,
        "code": "ready",
        "message": "the add-on can be recorded",
        "context": {
            "bytes": raw_size,
            "permissions": permissions,
            "signature": policy.get("signature", {}).get("required", False),
        },
        "requires_acknowledgement": True,
    }


def signature_state(repo: Path) -> str:
    policy = load_install_policy(repo)
    return "verified" if policy.get("signature", {}).get("required", False) else "unverified"


def refusal_context(repo: Path, manifest: WebExtensionManifest) -> dict:
    policy = load_install_policy(repo)
    refused = [permission for permission in manifest.declared_permissions() if permission in policy.get("prohibited_permissions", [])]
    return {"prohibited_permissions": policy.get("prohibited_permissions", []), "refused": refused}
