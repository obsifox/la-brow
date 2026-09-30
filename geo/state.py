"""Deterministic environment state machine."""

from __future__ import annotations

from enum import Enum

from geo.errors import EnvironmentConflictError


class EnvironmentState(str, Enum):
    UNKNOWN = "UNKNOWN"
    DETECTING = "DETECTING"
    DETECTED = "DETECTED"
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"
    HYBRID = "HYBRID"
    CONFLICT = "CONFLICT"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


TERMINAL_STATES = {EnvironmentState.DISABLED}

ALLOWED_TRANSITIONS: dict[EnvironmentState, set[EnvironmentState]] = {
    EnvironmentState.UNKNOWN: {EnvironmentState.DETECTING, EnvironmentState.MANUAL, EnvironmentState.AUTOMATIC, EnvironmentState.HYBRID, EnvironmentState.DISABLED, EnvironmentState.ERROR},
    EnvironmentState.DETECTING: {
        EnvironmentState.DETECTED,
        EnvironmentState.MANUAL,
        EnvironmentState.AUTOMATIC,
        EnvironmentState.HYBRID,
        EnvironmentState.CONFLICT,
        EnvironmentState.ERROR,
        EnvironmentState.DISABLED,
    },
    EnvironmentState.DETECTED: {EnvironmentState.AUTOMATIC, EnvironmentState.HYBRID, EnvironmentState.CONFLICT, EnvironmentState.ERROR, EnvironmentState.DISABLED, EnvironmentState.UNKNOWN},
    EnvironmentState.MANUAL: {EnvironmentState.CONFLICT, EnvironmentState.ERROR, EnvironmentState.DISABLED, EnvironmentState.UNKNOWN, EnvironmentState.HYBRID},
    EnvironmentState.AUTOMATIC: {EnvironmentState.CONFLICT, EnvironmentState.ERROR, EnvironmentState.DISABLED, EnvironmentState.UNKNOWN, EnvironmentState.HYBRID, EnvironmentState.MANUAL},
    EnvironmentState.HYBRID: {EnvironmentState.CONFLICT, EnvironmentState.ERROR, EnvironmentState.DISABLED, EnvironmentState.UNKNOWN, EnvironmentState.MANUAL, EnvironmentState.AUTOMATIC},
    EnvironmentState.CONFLICT: {EnvironmentState.DETECTING, EnvironmentState.MANUAL, EnvironmentState.AUTOMATIC, EnvironmentState.HYBRID, EnvironmentState.ERROR, EnvironmentState.DISABLED, EnvironmentState.UNKNOWN},
    EnvironmentState.ERROR: {EnvironmentState.UNKNOWN, EnvironmentState.DETECTING, EnvironmentState.MANUAL, EnvironmentState.DISABLED},
    EnvironmentState.DISABLED: {EnvironmentState.UNKNOWN},
}


class EnvironmentStateMachine:
    """Validates transitions and records deterministic transition history."""

    def __init__(self, initial: EnvironmentState = EnvironmentState.UNKNOWN) -> None:
        self.state = initial
        self.history: list[dict] = [{"from": None, "to": initial.value, "reason": "initial"}]

    def can_transition(self, target: EnvironmentState) -> bool:
        return target in ALLOWED_TRANSITIONS.get(self.state, set())

    def transition(self, target: EnvironmentState, reason: str) -> EnvironmentState:
        if target is self.state:
            return self.state
        if not self.can_transition(target):
            raise EnvironmentConflictError(
                "transition rejected by environment state machine",
                current=self.state.value,
                requested=target.value,
                reason=reason,
            )
        previous = self.state
        self.state = target
        self.history.append({"from": previous.value, "to": target.value, "reason": reason})
        return self.state

    def as_dict(self) -> dict:
        return {"state": self.state.value, "history": list(self.history)}
