"""HTTP route handlers for the application programming interface."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from api.settings_store import SettingsStore, utc_stamp
from application.service import DEFAULT_PROFILE, EnvironmentService
from diagnostics.redaction import RedactionLevel
from dns.diagnostics import DnsDiagnosticCenter
from dns.engine import DnsEngine
from extensions.compat import CompatibilityEngine
from extensions.manifest import ManifestError
from extensions.store import ExtensionStore, ExtensionStoreError
from extensions.themes import ThemeSpecError
from profiles.errors import ProfileError
from profiles.schema import CURRENT_PROFILE_VERSION, normalize, validate
from profiles.store import ProfileStore
from webrtc.policy import WebRtcPolicy, describe as describe_webrtc

MAX_REQUEST_BYTES = 262144
SCANNERS = ("emoji", "comment", "english", "branding")
SCAN_CACHE_SECONDS = 20.0


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, detail: object = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.detail = detail

    def as_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "detail": self.detail}}


class Api:
    """Binds the environment platform to a request and response oriented interface."""

    def __init__(self, repo: Path) -> None:
        self.repo = Path(repo)
        self.service = EnvironmentService(self.repo)
        self.store = ProfileStore(self.repo / "var")
        self.settings = SettingsStore(self.repo / "var")
        self.version = "0.1.0"
        self.scan_cache: list[dict] = []
        self.scan_cache_at = 0.0
        self.scan_cache_stamp = utc_stamp()
        self.extensions = ExtensionStore(self.repo)
        self.compatibility = CompatibilityEngine(self.repo)

    def health(self, query: dict) -> dict:
        return {
            "status": "OK",
            "application": "LA Brow",
            "version": self.version,
            "profile_version": CURRENT_PROFILE_VERSION,
            "generated_at": utc_stamp(),
            "capabilities": [
                "environment_resolution",
                "profiles",
                "resolvers",
                "dns_probe",
                "diagnostics",
                "identity",
                "desktop_theme_compatibility",
                "desktop_addon_compatibility",
            ],
        }

    def settings_get(self, query: dict) -> dict:
        return {"settings": self.settings.load()}

    def settings_put(self, query: dict, body: dict) -> dict:
        incoming = body.get("settings", body)
        if not isinstance(incoming, dict):
            raise ApiError(400, "invalid_body", "settings payload must be an object")
        saved = self.settings.save(incoming)
        return {"settings": saved, "saved_at": utc_stamp()}

    def environment(self, query: dict) -> dict:
        settings = self.settings.load()
        url = query.get("url", [settings["default_url"]])[0]
        profile_id = query.get("profile", [settings["active_profile"]])[0]
        resolver_id = query.get("resolver", [settings["resolver_profile"]])[0]
        privacy = query.get("privacy", [settings["privacy_preset"]])[0]
        private_value = query.get("private", [str(settings["private_browsing"]).lower()])[0]
        private_browsing = private_value in {"1", "true", "yes"}
        resolver = None if resolver_id in {"", "none", "system"} else resolver_id
        self._read_profile(profile_id)
        try:
            snapshot = self.service.resolve(
                url=url,
                profile_id=profile_id,
                resolver_id=resolver,
                privacy_preset=privacy,
                private_browsing=private_browsing,
            )
        except KeyError as error:
            raise ApiError(404, "profile_not_found", str(error)) from error
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        return {"snapshot": snapshot, "generated_at": utc_stamp()}

    def profiles_list(self, query: dict) -> dict:
        profiles = self.store.list_profiles()
        stored = [entry["id"] for entry in profiles]
        available = [{"id": "default", "name": DEFAULT_PROFILE["name"], "source": "built-in", "profile_version": DEFAULT_PROFILE["profile_version"]}]
        for entry in profiles:
            available.append({"id": entry["id"], "name": entry.get("name"), "source": "store", "profile_version": entry.get("profile_version")})
        return {
            "profiles": available,
            "stored_ids": stored,
            "current_version": CURRENT_PROFILE_VERSION,
            "built_in": DEFAULT_PROFILE,
        }

    def profile_get(self, profile_id: str, query: dict) -> dict:
        profile = self._read_profile(profile_id)
        return {"id": profile_id, "profile": profile}

    def profile_put(self, profile_id: str, query: dict, body: dict) -> dict:
        payload = body.get("profile", body)
        if not isinstance(payload, dict):
            raise ApiError(400, "invalid_body", "profile payload must be an object")
        try:
            saved = self.store.save(payload, profile_id)
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        return {"saved": saved, "profile": self._read_profile(saved["id"])}

    def profile_delete(self, profile_id: str, query: dict) -> dict:
        try:
            result = self.store.delete(profile_id)
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        return result

    def profile_validate(self, query: dict, body: dict) -> dict:
        payload = body.get("profile", body)
        try:
            profile = normalize(payload)
            validate(profile, allow_unknown=False)
        except ProfileError as error:
            return {"status": "INVALID", "error": error.as_dict()}
        except Exception as error:
            return {"status": "INVALID", "error": {"code": "validation", "message": str(error)}}
        return {"status": "VALID", "profile": profile}

    def profile_import(self, query: dict, body: dict) -> dict:
        payload = body.get("payload")
        profile_id = body.get("profile_id")
        dry_run = bool(body.get("dry_run", False))
        if not isinstance(payload, str) or not payload.strip():
            raise ApiError(400, "invalid_body", "import requires a payload string")
        try:
            result = self.store.import_payload(payload, profile_id=profile_id, dry_run=dry_run)
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        return result

    def profile_export(self, profile_id: str, query: dict) -> dict:
        profile = self._read_profile(profile_id)
        from profiles.integrity import envelope

        return {"id": profile_id, "payload": json.dumps(envelope(profile), indent=2, sort_keys=True)}

    def profile_rollback(self, profile_id: str, query: dict) -> dict:
        try:
            return self.store.rollback(profile_id)
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error

    def resolvers(self, query: dict) -> dict:
        profiles = [profile.as_dict() for profile in self.service.resolver_profiles.values()]
        return {"resolvers": profiles, "count": len(profiles)}

    def dns_probe(self, query: dict, body: dict) -> dict:
        resolver_id = body.get("resolver") or query.get("resolver", ["system"])[0]
        name = body.get("name") or query.get("name", ["example.com"])[0]
        record_type = (body.get("type") or query.get("type", ["A"])[0]).upper()
        profile = self.service.resolver_profiles.get(resolver_id)
        if profile is None:
            raise ApiError(404, "resolver_not_found", f"unknown resolver profile: {resolver_id}")
        engine = DnsEngine(profile)
        center = DnsDiagnosticCenter(engine, probe_name=name)
        probe = center.probe(record_type)
        report = center.report(profile_source="application-programming-interface")
        return {"probe": probe, "diagnostics": report, "generated_at": utc_stamp()}

    def dns_diagnostics(self, query: dict) -> dict:
        resolver_id = query.get("resolver", ["system"])[0]
        profile = self.service.resolver_profiles.get(resolver_id)
        if profile is None:
            raise ApiError(404, "resolver_not_found", f"unknown resolver profile: {resolver_id}")
        engine = DnsEngine(profile)
        center = DnsDiagnosticCenter(engine)
        return {"diagnostics": center.report(profile_source="application-programming-interface"), "integrity": engine.integrity_check()}

    def diagnostics(self, query: dict) -> dict:
        level_name = query.get("level", [self.settings.load()["diagnostics_level"]])[0]
        try:
            level = RedactionLevel(level_name)
        except ValueError as error:
            raise ApiError(400, "invalid_level", "diagnostics level must be full, redacted or minimal") from error
        settings = self.settings.load()
        profile_id = query.get("profile", [settings["active_profile"]])[0]
        resolver_id = query.get("resolver", [settings["resolver_profile"]])[0]
        resolver = None if resolver_id in {"", "none", "system"} else resolver_id
        try:
            report = self.service.diagnostics_export(level.value, profile_id=profile_id)
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        if resolver is not None:
            report["environment"]["resolver_requested"] = resolver
        return {"report": report, "level": level.value}

    def consistency(self, query: dict) -> dict:
        snapshot = self.environment(query)["snapshot"]
        return {"consistency": snapshot["consistency"], "status": snapshot["status"], "state": snapshot["state"]["state"]}

    def identity(self, query: dict) -> dict:
        identity = self.repo / "assets/identity"
        report = json.loads((identity / "identity-report.json").read_text(encoding="utf-8"))
        return {
            "report": report,
            "assets": {
                "icon": (identity / "icon.svg").read_text(encoding="utf-8"),
                "symbol": (identity / "icon-symbol.svg").read_text(encoding="utf-8"),
                "mask": (identity / "icon-mask.svg").read_text(encoding="utf-8"),
                "monochrome": (identity / "icon-monochrome.svg").read_text(encoding="utf-8"),
            },
        }

    def scans(self, query: dict) -> dict:
        refresh = query.get("refresh", ["false"])[0] in {"1", "true", "yes"}
        now = time.time()
        if not refresh and self.scan_cache and now - self.scan_cache_at < SCAN_CACHE_SECONDS:
            return {"scans": self.scan_cache, "cached": True, "generated_at": self.scan_cache_stamp}
        artifacts = self.repo / ".eng/artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        results = []
        for name in SCANNERS:
            target = artifacts / f"{name}_scan.json"
            completed = subprocess.run(
                [sys.executable, f"tools/scanners/{name}_scan.py", "--repo", ".", "--json-out", str(target)],
                cwd=self.repo,
                capture_output=True,
                text=True,
                timeout=120,
            )
            payload = {}
            if target.is_file():
                payload = json.loads(target.read_text(encoding="utf-8"))
            results.append(
                {
                    "scanner": name,
                    "status": payload.get("status", "PASS" if completed.returncode == 0 else "FAIL"),
                    "violations": payload.get("violation_count", 0),
                    "exempted_files": len(payload.get("exempted_files", [])),
                    "exit_code": completed.returncode,
                }
            )
        self.scan_cache = results
        self.scan_cache_at = time.time()
        self.scan_cache_stamp = utc_stamp()
        return {"scans": results, "cached": False, "generated_at": self.scan_cache_stamp}

    def extensions_list(self, query: dict) -> dict:
        listing = self.extensions.list_records()
        listing["runtime"] = self.compatibility.runtime()
        listing["notice"] = self.compatibility.notice()
        return listing

    def extensions_inspect(self, query: dict, body: dict) -> dict:
        manifest = body.get("manifest", body)
        if not isinstance(manifest, dict):
            raise ApiError(400, "invalid_body", "manifest payload must be an object")
        try:
            return self.extensions.inspect(manifest)
        except ManifestError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        except ThemeSpecError as error:
            raise ApiError(400, error.code, error.message, error.context) from error

    def extensions_install(self, query: dict, body: dict) -> dict:
        manifest = body.get("manifest", body)
        if not isinstance(manifest, dict):
            raise ApiError(400, "invalid_body", "manifest payload must be an object")
        identifier = body.get("id")
        acknowledged = bool(body.get("acknowledged", False))
        try:
            record = self.extensions.install(manifest, identifier=str(identifier) if identifier else None, acknowledged=acknowledged)
        except ExtensionStoreError as error:
            status = 409 if error.code in {"notice_not_acknowledged", "prohibited_permission", "prohibited_section"} else 400
            raise ApiError(status, error.code, error.message, error.context) from error
        except ManifestError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
        return {"installed": record, "notice": record["notice_text"]}

    def extensions_remove(self, identifier: str, query: dict) -> dict:
        try:
            return self.extensions.remove(identifier)
        except ExtensionStoreError as error:
            raise ApiError(404, "extension_not_found", error.message, error.context) from error

    def themes(self, query: dict) -> dict:
        listing = self.extensions.list_records()
        return {
            "themes": [entry["theme"] for entry in listing["themes"]],
            "active_theme": self.extensions.active_theme_spec(),
            "notice": listing["notice"],
        }

    def themes_activate(self, query: dict, body: dict) -> dict:
        identifier = body.get("id") or body.get("theme_id")
        if not identifier:
            raise ApiError(400, "invalid_body", "an identifier is required to activate a theme")
        try:
            return self.extensions.activate_theme(str(identifier))
        except ExtensionStoreError as error:
            status = 404 if error.code == "extension_store_error" and "not found" in error.message else 400
            raise ApiError(status, error.code, error.message, error.context) from error

    def compat_matrix(self, query: dict) -> dict:
        summary = self.compatibility.matrix_summary()
        listing = self.extensions.list_records()
        summary["installed"] = {
            "count": listing["count"],
            "active_theme": listing["active_theme"],
            "signature_state": listing["signature_state"],
        }
        return summary

    def webrtc(self, query: dict) -> dict:
        entries = [describe_webrtc(policy) for policy in WebRtcPolicy]
        return {"policies": entries}

    def events(self, query: dict) -> dict:
        snapshot = self.environment(query)["snapshot"]
        return {"events": snapshot["events"], "state": snapshot["state"]}

    def _read_profile(self, profile_id: str) -> dict:
        if profile_id == "default":
            return dict(DEFAULT_PROFILE)
        if not self.store.path_for(profile_id).is_file():
            raise ApiError(404, "profile_not_found", f"profile not found: {profile_id}")
        try:
            return self.store.load(profile_id)
        except ProfileError as error:
            raise ApiError(400, error.code, error.message, error.context) from error
