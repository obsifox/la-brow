"""Command line interface for the environment platform."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from application.service import EnvironmentService, DEFAULT_PROFILE
from diagnostics.export import export_json
from diagnostics.redaction import RedactionLevel
from profiles.migrations import supported_migration_path
from profiles.schema import CURRENT_PROFILE_VERSION
from profiles.store import ProfileStore

REPO_ROOT = Path(__file__).resolve().parent.parent


def emit(payload: dict | list, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        for item in payload:
            print(json.dumps(item, sort_keys=True))
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_environment(arguments) -> int:
    service = EnvironmentService(REPO_ROOT)
    snapshot = service.resolve(
        url=arguments.url,
        profile_id=arguments.profile,
        resolver_id=arguments.resolver,
        privacy_preset=arguments.privacy,
        private_browsing=arguments.private,
    )
    if arguments.summary:
        summary = {
            "status": snapshot["status"],
            "state": snapshot["state"]["state"],
            "geo_source": None if snapshot["geo"] is None else snapshot["geo"]["source"],
            "country": snapshot["effective_profile"].get("country"),
            "timezone": None if snapshot["timezone"] is None else snapshot["timezone"]["zone"],
            "locale": None if snapshot["locale"] is None else snapshot["locale"]["surfaces"]["browser_locale"],
            "dns_protocol": "not-configured" if snapshot["dns"] is None else snapshot["dns"]["resolver_protocol"],
            "consistency": snapshot["consistency"]["status"],
            "stages": [{stage["stage"]: stage["status"]} for stage in snapshot["stages"]],
        }
        emit(summary, arguments.json)
        return 0 if snapshot["status"] == "OK" else 2
    emit(snapshot, True)
    return 0 if snapshot["status"] == "OK" else 2


def command_geo(arguments) -> int:
    service = EnvironmentService(REPO_ROOT)
    profile = service.load_profile(arguments.profile)
    snapshot = service.resolve(profile_id=arguments.profile, private_browsing=arguments.private)
    emit({"geo": snapshot["geo"], "policy": snapshot["policy"], "consistency": snapshot["consistency"], "profile": profile.get("name")}, True)
    return 0


def command_dns(arguments) -> int:
    service = EnvironmentService(REPO_ROOT)
    if arguments.list_profiles:
        emit([profile.as_dict() for profile in service.resolver_profiles.values()], True)
        return 0
    if not arguments.resolver:
        emit({"error": "resolver identifier is required unless --list-profiles is used"}, True)
        return 2
    result = service.dns_probe(arguments.resolver, arguments.name, arguments.type)
    emit(result, True)
    return 0 if result.get("status") == "SUCCESS" else 1


def command_profiles(arguments) -> int:
    store = ProfileStore(REPO_ROOT / "var")
    if arguments.action == "list":
        emit({"profiles": store.list_profiles(), "current_version": CURRENT_PROFILE_VERSION, "migrations": supported_migration_path()}, True)
        return 0
    if arguments.action == "validate":
        from profiles.schema import validate

        validate(json.loads(Path(arguments.file).read_text(encoding="utf-8")))
        emit({"status": "VALID", "file": arguments.file}, True)
        return 0
    if arguments.action == "import":
        raw = Path(arguments.file).read_text(encoding="utf-8")
        result = store.import_payload(raw, profile_id=arguments.profile_id, dry_run=arguments.dry_run)
        emit(result, True)
        return 0
    if arguments.action == "export":
        emit({"payload": store.export(arguments.profile_id)}, True)
        return 0
    if arguments.action == "migrate":
        from profiles.migrations import migrate

        migrated, applied = migrate(json.loads(Path(arguments.file).read_text(encoding="utf-8")))
        emit({"profile": migrated, "migrations_applied": applied}, True)
        return 0
    emit({"error": f"unsupported action {arguments.action}"}, True)
    return 2


def command_diagnostics(arguments) -> int:
    service = EnvironmentService(REPO_ROOT)
    level = RedactionLevel(arguments.level)
    snapshot = service.resolve(profile_id=arguments.profile, resolver_id=arguments.resolver)
    report = export_json(snapshot, level)
    if arguments.out:
        Path(arguments.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        emit({"written": arguments.out, "level": level.value, "consistency": snapshot["consistency"]["status"]}, True)
        return 0
    emit(report, True)
    return 0


def command_shell(arguments) -> int:
    from browser.shell import BrowserShell, PermissionKind, SessionMode

    shell = BrowserShell(session_mode=SessionMode.PRIVATE if arguments.private else SessionMode.NORMAL)
    for url in arguments.url or ["about:newtab"]:
        shell.open_tab(url)
    shell.set_permission(PermissionKind.GEOLOCATION, "prompt")
    emit(
        {
            "session": shell.session_snapshot(),
            "permissions": {kind.value: shell.effective_permission(kind) for kind in PermissionKind},
        },
        True,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labrowctl", description="LA Brow environment control interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    environment = subparsers.add_parser("environment", help="resolve the environment pipeline")
    environment.add_argument("--url")
    environment.add_argument("--profile", default="default")
    environment.add_argument("--resolver")
    environment.add_argument("--privacy", default="balanced")
    environment.add_argument("--private", action="store_true")
    environment.add_argument("--summary", action="store_true")
    environment.add_argument("--json", action="store_true")
    environment.set_defaults(handler=command_environment)

    geo = subparsers.add_parser("geo", help="inspect geo resolution")
    geo.add_argument("--profile", default="default")
    geo.add_argument("--private", action="store_true")
    geo.set_defaults(handler=command_geo)

    dns = subparsers.add_parser("dns", help="inspect and probe resolvers")
    dns.add_argument("--resolver")
    dns.add_argument("--name", default="example.com")
    dns.add_argument("--type", default="A")
    dns.add_argument("--list-profiles", action="store_true")
    dns.set_defaults(handler=command_dns)

    profiles = subparsers.add_parser("profiles", help="manage versioned profiles")
    profiles.add_argument("action", choices=["list", "validate", "import", "export", "migrate"])
    profiles.add_argument("--file")
    profiles.add_argument("--profile-id")
    profiles.add_argument("--dry-run", action="store_true")
    profiles.set_defaults(handler=command_profiles)

    diagnostics = subparsers.add_parser("diagnostics", help="export diagnostics")
    diagnostics.add_argument("--level", default="redacted", choices=["full", "redacted", "minimal"])
    diagnostics.add_argument("--profile", default="default")
    diagnostics.add_argument("--resolver")
    diagnostics.add_argument("--out")
    diagnostics.set_defaults(handler=command_diagnostics)

    shell = subparsers.add_parser("shell", help="inspect the browser shell session model")
    shell.add_argument("--url", action="append")
    shell.add_argument("--private", action="store_true")
    shell.set_defaults(handler=command_shell)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    sys.exit(main())
