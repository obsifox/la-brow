"""Environment state machine tests."""

from __future__ import annotations

import pytest

from geo.errors import EnvironmentConflictError
from geo.state import ALLOWED_TRANSITIONS, EnvironmentState, EnvironmentStateMachine


def test_initial_state_is_unknown_and_persistent():
    machine = EnvironmentStateMachine()
    assert machine.state is EnvironmentState.UNKNOWN
    assert machine.history[0]["to"] == "UNKNOWN"


def test_deterministic_path_to_manual_state():
    machine = EnvironmentStateMachine()
    machine.transition(EnvironmentState.DETECTING, "pipeline started")
    machine.transition(EnvironmentState.MANUAL, "virtual provider resolved")
    assert machine.state is EnvironmentState.MANUAL
    assert [entry["to"] for entry in machine.history] == ["UNKNOWN", "DETECTING", "MANUAL"]


def test_disabled_state_returns_to_unknown_only():
    machine = EnvironmentStateMachine(EnvironmentState.DISABLED)
    assert machine.can_transition(EnvironmentState.UNKNOWN) is True
    assert machine.can_transition(EnvironmentState.CONFLICT) is False


def test_idempotent_transition_is_accepted():
    machine = EnvironmentStateMachine()
    assert machine.transition(EnvironmentState.UNKNOWN, "no change") is EnvironmentState.UNKNOWN
    assert len(machine.history) == 1


def test_missing_transition_is_rejected():
    machine = EnvironmentStateMachine(EnvironmentState.DISABLED)
    with pytest.raises(EnvironmentConflictError):
        machine.transition(EnvironmentState.MANUAL, "illegal jump")


def test_every_state_has_transition_definition():
    for state in EnvironmentState:
        assert state in ALLOWED_TRANSITIONS
        assert ALLOWED_TRANSITIONS[state]
