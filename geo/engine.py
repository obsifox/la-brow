"""Geo engine that resolves an environment request through a single provider."""

from __future__ import annotations

from geo.errors import PhysicalFallbackForbiddenError, ProviderUnavailableError
from geo.events import EventBus
from geo.models import GeoFix, GeoMode, GeoRequest, RandomizationScope
from geo.providers import GeoProvider
from geo.state import EnvironmentState, EnvironmentStateMachine

PHYSICAL_ALLOWED_MODES = {GeoMode.AUTOMATIC}


class GeoEngine:
    """Single entry point for geo resolution with explicit failure behaviour."""

    def __init__(
        self,
        providers: dict[GeoMode, GeoProvider],
        event_bus: EventBus | None = None,
        state_machine: EnvironmentStateMachine | None = None,
    ) -> None:
        self.providers = providers
        self.events = event_bus or EventBus()
        self.state = state_machine or EnvironmentStateMachine()
        self.last_fix: GeoFix | None = None
        self.failures: list[dict] = []

    def _provider_for(self, mode: GeoMode) -> GeoProvider:
        provider = self.providers.get(mode)
        if provider is None:
            raise ProviderUnavailableError("no provider registered for the requested mode", mode=mode.value)
        return provider

    def resolve(self, request: GeoRequest) -> GeoFix:
        provider = self._provider_for(request.mode)
        self.events.emit("geo.resolve.started", actor="geo-engine", mode=request.mode.value, provider=provider.provider_id)
        try:
            fix = provider.resolve(request)
        except ProviderUnavailableError as error:
            self._record_failure(error, request)
            self._set_state(EnvironmentState.ERROR, f"provider failure: {error.code}")
            if request.block_physical_fallback and request.mode is not GeoMode.AUTOMATIC:
                raise PhysicalFallbackForbiddenError(
                    "virtual environment could not be resolved and physical fallback is forbidden",
                    requested_mode=request.mode.value,
                    provider=provider.provider_id,
                    original_error=error.as_dict(),
                ) from error
            raise
        self.last_fix = fix
        self._set_state(self._state_for_mode(fix.mode), f"resolved by {fix.provider_id}")
        self.events.emit(
            "geo.changed",
            actor="geo-engine",
            source=fix.source.value,
            mode=fix.mode.value,
            provider=fix.provider_id,
            confidence=fix.confidence,
            seed=fix.seed,
        )
        return fix

    def _record_failure(self, error: ProviderUnavailableError, request: GeoRequest) -> None:
        self.failures.append({"code": error.code, "message": error.message, "mode": request.mode.value, "context": error.context})
        self.events.emit("geo.resolve.failed", severity="ERROR", actor="geo-engine", code=error.code, mode=request.mode.value)

    def _state_for_mode(self, mode: GeoMode) -> EnvironmentState:
        if mode is GeoMode.DISABLED:
            return EnvironmentState.DISABLED
        if mode in {GeoMode.MANUAL}:
            return EnvironmentState.MANUAL
        if mode is GeoMode.AUTOMATIC:
            return EnvironmentState.AUTOMATIC
        if mode is GeoMode.HYBRID:
            return EnvironmentState.HYBRID
        return EnvironmentState.UNKNOWN

    def _set_state(self, target: EnvironmentState, reason: str) -> None:
        if self.state.state is target:
            return
        if self.state.can_transition(target):
            self.state.transition(target, reason)
        else:
            self.state.transition(EnvironmentState.DETECTING, f"reset before {target.value}")
            self.state.transition(target, reason)

    def describe(self) -> dict:
        return {
            "state": self.state.as_dict(),
            "providers": sorted(mode.value for mode in self.providers),
            "last_fix": None if self.last_fix is None else self.last_fix.as_dict(),
            "failures": list(self.failures),
        }


def build_engine(profile: dict, providers: dict[GeoMode, GeoProvider], event_bus: EventBus | None = None) -> GeoEngine:
    mode = GeoMode(profile.get("geolocation_mode", GeoMode.MANUAL.value))
    ordered = {mode: providers[mode], **{key: value for key, value in providers.items() if key is not mode}}
    return GeoEngine(ordered, event_bus=event_bus)


def request_from_profile(profile: dict, session_id: str | None = None) -> GeoRequest:
    from geo.providers import circle_from_profile, default_scope

    scope = default_scope(profile)
    circle = None
    if profile.get("latitude") is not None or profile.get("country"):
        circle = circle_from_profile(profile)
    return GeoRequest(
        mode=GeoMode(profile.get("geolocation_mode", GeoMode.MANUAL.value)),
        circle=circle,
        randomization_scope=scope if scope is not RandomizationScope.NONE else RandomizationScope.NONE,
        block_physical_fallback=bool(profile.get("block_physical_fallback", True)),
        session_id=session_id,
        profile_id=profile.get("name"),
    )
