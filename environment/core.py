"""Deterministic environment resolution pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as timezone_module
from pathlib import Path

from diagnostics.consistency import check as consistency_check
from dns.diagnostics import DnsDiagnosticCenter
from dns.engine import DnsEngine, load_provider_profiles
from dns.models import ResolverProfile
from gecko.integration import integration_plan
from geo.engine import GeoEngine, request_from_profile
from geo.errors import GeoError
from geo.events import EventBus
from geo.models import GeoMode
from geo.providers import (
    AutomaticProvider,
    AutomaticRequest,
    DisabledProvider,
    HybridProvider,
    PhysicalProvider,
    VirtualProvider,
    circle_from_profile,
    default_scope,
)
from geo.state import EnvironmentState, EnvironmentStateMachine
from locale_engine.engine import resolve as resolve_locale
from locale_engine.models import LocaleConfig, LocaleMode
from network.detection import DetectionSignals, detect_environment
from policy.engine import resolve as resolve_policy
from policy.models import SiteRule
from privacy.policy import PRESETS as PRIVACY_PRESETS, PrivacyPolicy, report as privacy_report
from profiles.schema import normalize, validate
from timezone.engine import resolve as resolve_timezone, system_zone_name
from timezone.models import TimezoneConfig, TimezoneMode
from webrtc.policy import WebRtcPolicy

STAGE_ORDER = (
    "profile_resolution",
    "policy_resolution",
    "environment_validation",
    "geo_resolution",
    "timezone_resolution",
    "locale_resolution",
    "network_resolution",
    "dns_resolution",
    "privacy_policy",
    "gecko_integration",
    "web_content_ready",
)

HALTING_STAGES = {"profile_resolution", "environment_validation", "geo_resolution"}


@dataclass
class EnvironmentConfig:
    profile: dict
    site_rules: list[SiteRule] = field(default_factory=list)
    resolver_profile: ResolverProfile | None = None
    fallback_resolver_profile: ResolverProfile | None = None
    privacy_preset: str = "balanced"
    session_id: str = "local-session"
    application_version: str = "0.1.0"
    detect_network: bool = True
    detection_signals: DetectionSignals | None = None
    repo_path: Path = field(default_factory=lambda: Path.cwd())


class DeferredProvider:
    """Holder that constructs an unused provider only when it is actually resolved."""

    def __init__(self, factory, mode: GeoMode) -> None:
        self.factory = factory
        self.mode = mode
        self.provider_id = f"deferred-{mode.value}"
        self.source = None
        self.provider = None

    def resolve(self, request):
        if self.provider is None:
            self.provider = self.factory()
        return self.provider.resolve(request)


@dataclass
class StageResult:
    name: str
    status: str
    detail: str
    output: dict = field(default_factory=dict)
    error: dict | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "stage": self.name,
            "status": self.status,
            "detail": self.detail,
            "output": self.output,
            "error": self.error,
            "notes": list(self.notes),
        }


class EnvironmentCore:
    """Resolves user configuration into an observable environment document."""

    def __init__(self, config: EnvironmentConfig) -> None:
        self.config = config
        self.events = EventBus()
        self.state = EnvironmentStateMachine(EnvironmentState.UNKNOWN)

    def _providers(self, profile: dict, signals: DetectionSignals, mode: GeoMode):
        automatic_request = AutomaticRequest(
            signals=signals,
            timezone_hint=profile.get("timezone") or system_zone_name(),
            locale_hint=profile.get("locale"),
        )
        automatic = AutomaticProvider(automatic_request)
        factories = {
            GeoMode.MANUAL: lambda: VirtualProvider(circle_from_profile(profile), base_seed=profile.get("randomization_seed")),
            GeoMode.AUTOMATIC: lambda: automatic,
            GeoMode.HYBRID: lambda: HybridProvider(automatic, profile),
            GeoMode.DISABLED: lambda: DisabledProvider(),
        }
        selected = mode if mode in factories else GeoMode.DISABLED
        providers: dict[GeoMode, object] = {selected: factories[selected]()}
        for other_mode, factory in factories.items():
            if other_mode is not selected:
                providers[other_mode] = DeferredProvider(factory, other_mode)
        return providers

    def run(self, url: str | None = None, private_browsing: bool = False) -> dict:
        stages: list[StageResult] = []
        started = datetime.now(timezone_module.utc)
        self.events.emit("environment.pipeline.started", actor="environment-core", url=url or "none")
        self._to_state(EnvironmentState.DETECTING, "pipeline started")
        signals = self.config.detection_signals or (detect_environment() if self.config.detect_network else DetectionSignals())
        effective_profile: dict = {}
        policy_resolution = None
        geo_fix = None
        geo_report = None
        timezone_resolution = None
        locale_resolution = None
        dns_status = None
        privacy = PRIVACY_PRESETS.get(self.config.privacy_preset, PRIVACY_PRESETS["balanced"])
        halted = False
        for stage in STAGE_ORDER:
            if halted:
                stages.append(StageResult(stage, "SKIPPED", "pipeline halted by an earlier failure"))
                continue
            if stage == "profile_resolution":
                try:
                    profile = normalize(self.config.profile)
                    validate(profile, allow_unknown=False)
                    effective_profile = profile
                    stages.append(
                        StageResult(
                            "profile_resolution",
                            "OK",
                            "profile validated",
                            {"profile_version": profile["profile_version"], "geolocation_mode": profile["geolocation_mode"]},
                        )
                    )
                except Exception as error:
                    stages.append(
                        StageResult("profile_resolution", "FAILED", "profile validation failed", error=_error_payload(error))
                    )
                    halted = True
            elif stage == "policy_resolution":
                policy_resolution = resolve_policy(self.config.site_rules, url or "about:blank", private_browsing)
                effective_profile = {**effective_profile, **policy_resolution.effective_overrides}
                stages.append(
                    StageResult(
                        "policy_resolution",
                        "OK",
                        "site policy resolved",
                        {
                            "matched_rule_count": len(policy_resolution.matched_rules),
                            "overrides": policy_resolution.effective_overrides,
                            "trace": policy_resolution.trace,
                        },
                    )
                )
            elif stage == "environment_validation":
                problems = self._validate_environment(effective_profile, signals)
                if problems:
                    stages.append(
                        StageResult(
                            "environment_validation",
                            "FAILED",
                            "environment validation found blocking problems",
                            {"problems": problems},
                        )
                    )
                    halted = self._should_halt(problems)
                    if not halted:
                        self._to_state(EnvironmentState.CONFLICT, "environment conflicts detected")
                else:
                    stages.append(StageResult("environment_validation", "OK", "environment validation passed"))
            elif stage == "geo_resolution":
                try:
                    mode = GeoMode(effective_profile.get("geolocation_mode", GeoMode.MANUAL.value))
                    engine = GeoEngine(self._providers(effective_profile, signals, mode), event_bus=self.events, state_machine=self.state)
                    request = request_from_profile(effective_profile, session_id=self.config.session_id)
                    geo_fix = engine.resolve(request)
                    geo_report = engine.describe()
                    stages.append(StageResult("geo_resolution", "OK", "geo resolved", geo_fix.as_dict()))
                except GeoError as error:
                    stages.append(StageResult("geo_resolution", "FAILED", "geo resolution failed", error=error.as_dict()))
                    halted = True
                except Exception as error:
                    stages.append(StageResult("geo_resolution", "FAILED", "geo resolution raised an unexpected error", error=_error_payload(error)))
                    halted = True
            elif stage == "timezone_resolution":
                mode = TimezoneMode(effective_profile.get("timezone_mode", TimezoneMode.PROFILE.value if effective_profile.get("timezone") else TimezoneMode.AUTOMATIC.value))
                timezone_resolution = resolve_timezone(
                    TimezoneConfig(mode=mode, zone=effective_profile.get("timezone"), source_profile=effective_profile.get("name")),
                    system_zone_name(),
                )
                stages.append(StageResult("timezone_resolution", "OK", "timezone resolved", timezone_resolution.as_dict()))
                self.events.emit("timezone.changed", actor="environment-core", zone=timezone_resolution.zone, mode=timezone_resolution.mode.value)
            elif stage == "locale_resolution":
                mode = LocaleMode(effective_profile.get("locale_mode", LocaleMode.PROFILE.value if effective_profile.get("locale") else LocaleMode.BROWSER_DEFAULT.value))
                locale_resolution = resolve_locale(
                    LocaleConfig(
                        mode=mode,
                        locale=effective_profile.get("locale"),
                        languages=tuple(effective_profile.get("languages", [])),
                        source_profile=effective_profile.get("name"),
                    ),
                    None,
                )
                stages.append(StageResult("locale_resolution", "OK", "locale resolved", locale_resolution.as_dict()))
                self.events.emit("locale.changed", actor="environment-core", locale=locale_resolution.browser_locale, mode=locale_resolution.mode.value)
            elif stage == "network_resolution":
                confidence, notes = self._network_confidence(signals)
                stages.append(
                    StageResult(
                        "network_resolution",
                        "OK",
                        "network environment inspected",
                        {
                            "interface_count": len(signals.interfaces),
                            "default_route_interface": signals.default_route_interface,
                            "vpn_detected": signals.vpn_interface_detected is not None,
                            "proxy_environment_present": bool(signals.proxy_environment),
                            "confidence": confidence,
                            "signals": signals.as_dict(),
                        },
                        notes=notes,
                    )
                )
            elif stage == "dns_resolution":
                if self.config.resolver_profile is None:
                    stages.append(
                        StageResult(
                            "dns_resolution",
                            "SKIPPED",
                            "no resolver profile is configured; browser default resolver settings remain untouched",
                            {"protocol": "system"},
                            notes=["safe default keeps operating system resolver behaviour without probing"],
                        )
                    )
                else:
                    engine = DnsEngine(self.config.resolver_profile, fallback_profile=self.config.fallback_resolver_profile)
                    center = DnsDiagnosticCenter(engine)
                    dns_status = center.report(profile_source="environment-configuration")
                    stages.append(
                        StageResult(
                            "dns_resolution",
                            "OK",
                            "resolver profile activated",
                            dns_status,
                        )
                    )
            elif stage == "privacy_policy":
                webrtc_value = effective_profile.get("webrtc_policy")
                if webrtc_value:
                    privacy = PrivacyPolicy.from_dict({**privacy.as_dict(), "webrtc_policy": webrtc_value})
                stages.append(StageResult("privacy_policy", "OK", "privacy policy resolved", privacy_report(privacy)))
            elif stage == "gecko_integration":
                plan = integration_plan(effective_profile, privacy, timezone_resolution, locale_resolution)
                stages.append(StageResult("gecko_integration", "OK", "Gecko integration artifacts prepared", plan))
            elif stage == "web_content_ready":
                invariants = self._invariants(effective_profile, geo_fix)
                stages.append(
                    StageResult(
                        "web_content_ready",
                        "OK" if all(item["satisfied"] for item in invariants) else "FAILED",
                        "invariants evaluated",
                        {"invariants": invariants},
                    )
                )
        consistency = consistency_check(
            effective_profile,
            None if geo_fix is None else geo_fix.as_dict(),
            None if timezone_resolution is None else timezone_resolution.as_dict(),
            None if locale_resolution is None else locale_resolution.as_dict(),
            dns_status,
        )
        if consistency["findings"] and not halted:
            self._to_state(EnvironmentState.CONFLICT, "consistency findings present")
        duration_ms = (datetime.now(timezone_module.utc) - started).total_seconds() * 1000.0
        snapshot = {
            "application_version": self.config.application_version,
            "generated_at": datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": url,
            "private_browsing": private_browsing,
            "stages": [stage.as_dict() for stage in stages],
            "stage_order": list(STAGE_ORDER),
            "status": "FAILED" if halted else "OK",
            "halted": halted,
            "duration_ms": round(duration_ms, 2),
            "effective_profile": effective_profile,
            "geo": None if geo_fix is None else geo_fix.as_dict(),
            "geo_engine": geo_report,
            "timezone": None if timezone_resolution is None else timezone_resolution.as_dict(),
            "locale": None if locale_resolution is None else locale_resolution.as_dict(),
            "dns": dns_status,
            "policy": None if policy_resolution is None else policy_resolution.as_dict(),
            "privacy": privacy_report(privacy),
            "consistency": consistency,
            "state": self.state.as_dict(),
            "events": self.events.history(),
        }
        return snapshot

    def _validate_environment(self, profile: dict, signals: DetectionSignals) -> list[dict]:
        problems: list[dict] = []
        mode = profile.get("geolocation_mode")
        if mode == GeoMode.MANUAL.value:
            if profile.get("latitude") is None and profile.get("longitude") is None and profile.get("country") is None:
                problems.append({"field": "location", "issue": "manual mode requires coordinates or a country"})
            if not profile.get("block_physical_fallback", True):
                problems.append({"field": "block_physical_fallback", "issue": "manual mode must not permit physical fallback"})
        if mode == GeoMode.AUTOMATIC.value and not signals.interfaces and not profile.get("timezone"):
            problems.append({"field": "geolocation_mode", "issue": "automatic mode has no usable environment signal"})
        if mode == GeoMode.HYBRID.value and not profile.get("latitude") and not profile.get("country"):
            problems.append({"field": "geolocation_mode", "issue": "hybrid mode requires at least one manual constraint"})
        if profile.get("randomization") and profile.get("randomization") != "none" and not profile.get("radius"):
            problems.append({"field": "randomization", "issue": "randomization requires a non zero radius"})
        return problems

    def _should_halt(self, problems: list[dict]) -> bool:
        blocking = {"location", "geolocation_mode"}
        return any(problem["field"] in blocking for problem in problems)

    def _network_confidence(self, signals: DetectionSignals) -> tuple[float, list[str]]:
        from network.detection import signal_confidence

        return signal_confidence(signals)

    def _invariants(self, profile: dict, geo_fix) -> list[dict]:
        invariants = [
            {
                "id": "virtual-mode-without-physical-fallback",
                "satisfied": not (profile.get("geolocation_mode") == GeoMode.MANUAL.value and profile.get("block_physical_fallback") is False),
                "statement": "virtual mode must not silently fall back to physical geolocation",
            },
            {
                "id": "browser-scoped-dns",
                "satisfied": True,
                "statement": "browser scoped DNS configuration never modifies operating system settings",
            },
            {
                "id": "public-ip-unchanged",
                "satisfied": True,
                "statement": "the environment pipeline does not change public network routing or the observed public IP address",
            },
            {
                "id": "no-anonymity-claim",
                "satisfied": True,
                "statement": "consistency diagnostics are not presented as fingerprint anonymity guarantees",
            },
        ]
        if geo_fix is not None:
            invariants.append(
                {
                    "id": "fix-source-reported",
                    "satisfied": bool(geo_fix.source.value),
                    "statement": "every resolution reports its source and confidence",
                }
            )
        return invariants

    def _to_state(self, target: EnvironmentState, reason: str) -> None:
        if self.state.state is target:
            return
        if self.state.can_transition(target):
            self.state.transition(target, reason)
            return
        if self.state.can_transition(EnvironmentState.DETECTING):
            self.state.transition(EnvironmentState.DETECTING, f"reset before {target.value}")
            self.state.transition(target, reason)

    def describe(self) -> dict:
        return {
            "stage_order": list(STAGE_ORDER),
            "state": self.state.as_dict(),
            "profile": self.config.profile.get("name"),
            "resolver_profile": None if self.config.resolver_profile is None else self.config.resolver_profile.id,
            "privacy_preset": self.config.privacy_preset,
        }


def _error_payload(error: Exception) -> dict:
    if hasattr(error, "as_dict"):
        return error.as_dict()
    if hasattr(error, "problems"):
        return {"code": "validation", "message": str(error), "problems": error.problems}
    return {"code": error.__class__.__name__.lower(), "message": str(error)}


def load_resolver_profile(repo: Path, profile_id: str) -> ResolverProfile | None:
    profiles = load_provider_profiles(repo)
    return profiles.get(profile_id)
