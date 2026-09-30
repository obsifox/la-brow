"""Service layer that composes environment, profile, DNS and diagnostic subsystems."""

from __future__ import annotations

from pathlib import Path

import yaml

from diagnostics.export import export_json
from diagnostics.redaction import RedactionLevel
from dns.engine import DnsEngine, load_provider_profiles
from dns.diagnostics import DnsDiagnosticCenter
from environment.core import EnvironmentConfig, EnvironmentCore, load_resolver_profile
from policy.models import SiteRule, PolicyScope
from profiles.store import ProfileStore

DEFAULT_PROFILE = {
    "name": "default",
    "profile_version": 2,
    "geolocation_mode": "manual",
    "country": "DE",
    "city": "Berlin",
    "latitude": 52.52,
    "longitude": 13.405,
    "radius": 5000,
    "accuracy_m": 5000,
    "randomization": "per_session",
    "randomization_seed": 20260101,
    "timezone": "Europe/Berlin",
    "locale": "en-US",
    "languages": ["en-US", "en"],
    "webrtc_policy": "privacy_enhanced",
}


class EnvironmentService:
    """Facade used by the command line interface and the control center."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.store = ProfileStore(repo / "var")
        self.resolver_profiles = load_provider_profiles(repo)

    def load_site_rules(self) -> list[SiteRule]:
        path = self.repo / "config/browser/site-policies.yaml"
        if not path.is_file():
            return []
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rules: list[SiteRule] = []
        for entry in payload.get("rules", []):
            rules.append(
                SiteRule(
                    id=entry["id"],
                    scope=PolicyScope(entry["scope"]),
                    pattern=entry.get("pattern", "*"),
                    overrides=dict(entry.get("overrides", {})),
                    priority=int(entry.get("priority", 0)),
                    enabled=bool(entry.get("enabled", True)),
                    description=entry.get("description", ""),
                )
            )
        return rules

    def load_profile(self, profile_id: str) -> dict:
        if profile_id == "default":
            return dict(DEFAULT_PROFILE)
        return self.store.load(profile_id)

    def build_core(
        self,
        profile_id: str = "default",
        resolver_id: str | None = None,
        privacy_preset: str = "balanced",
        site_rules: list[SiteRule] | None = None,
        detect_network: bool = True,
    ) -> EnvironmentCore:
        profile = self.load_profile(profile_id)
        resolver = self.resolver_profiles.get(resolver_id) if resolver_id else None
        fallback = self.resolver_profiles.get("system") if resolver is not None else None
        config = EnvironmentConfig(
            profile=profile,
            site_rules=self.load_site_rules() if site_rules is None else site_rules,
            resolver_profile=resolver,
            fallback_resolver_profile=fallback if resolver is not None and resolver.fallback_policy.value == "system_on_failure" else None,
            privacy_preset=privacy_preset,
            repo_path=self.repo,
            detect_network=detect_network,
        )
        return EnvironmentCore(config)

    def resolve(
        self,
        url: str | None = None,
        profile_id: str = "default",
        resolver_id: str | None = None,
        privacy_preset: str = "balanced",
        private_browsing: bool = False,
    ) -> dict:
        core = self.build_core(profile_id, resolver_id, privacy_preset)
        return core.run(url=url, private_browsing=private_browsing)

    def dns_probe(self, resolver_id: str, query_name: str = "example.com", record_type: str = "A") -> dict:
        profile = self.resolver_profiles.get(resolver_id)
        if profile is None:
            raise KeyError(f"unknown resolver profile: {resolver_id}")
        engine = DnsEngine(profile)
        center = DnsDiagnosticCenter(engine, probe_name=query_name)
        return center.probe(record_type=record_type)

    def diagnostics_export(self, level: str = "redacted", profile_id: str = "default") -> dict:
        snapshot = self.resolve(profile_id=profile_id)
        return export_json(snapshot, RedactionLevel(level))

    def sample_site_rules(self) -> list[SiteRule]:
        return [
            SiteRule(
                id="rule-example-domain",
                scope=PolicyScope.DOMAIN,
                pattern="example.com",
                overrides={"timezone": "Europe/Berlin", "locale": "en-US"},
                priority=10,
                description="documented example policy",
            ),
            SiteRule(
                id="rule-origin-override",
                scope=PolicyScope.ORIGIN,
                pattern="https://example.com",
                overrides={"radius": 15000},
                priority=5,
                description="origin scope overrides domain scope for the same field",
            ),
            SiteRule(
                id="rule-private-browsing",
                scope=PolicyScope.PRIVATE_BROWSING,
                pattern="*",
                overrides={"randomization": "per_query"},
                priority=1,
                description="private browsing increases randomization scope",
            ),
        ]
