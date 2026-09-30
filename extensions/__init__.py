"""Desktop Firefox theme and extension compatibility layer."""

from extensions.compat import CompatibilityEngine
from extensions.manifest import ManifestError, WebExtensionManifest, parse_manifest
from extensions.policy import evaluate_install, load_install_policy
from extensions.store import ExtensionStore
from extensions.themes import theme_spec

__all__ = [
    "CompatibilityEngine",
    "ExtensionStore",
    "ManifestError",
    "WebExtensionManifest",
    "evaluate_install",
    "load_install_policy",
    "parse_manifest",
    "theme_spec",
]
