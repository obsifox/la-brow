"""Structured event bus for environment subsystem observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as timezone_module
from typing import Callable

SEVERITY_LEVELS = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL")

SENSITIVE_KEY_FRAGMENTS = ("secret", "token", "password", "credential", "cookie", "authorization")


@dataclass(frozen=True)
class Event:
    name: str
    severity: str
    actor: str
    payload: dict = field(default_factory=dict)
    timestamp: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "severity": self.severity,
            "actor": self.actor,
            "payload": redact_payload(self.payload),
            "timestamp": self.timestamp,
        }


def utc_now() -> str:
    return datetime.now(timezone_module.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact_payload(payload: dict) -> dict:
    redacted = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
            redacted[key] = "[redacted]"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        else:
            redacted[key] = value
    return redacted


class EventBus:
    """Collects structured events and forwards them to subscribers."""

    def __init__(self, capacity: int = 512) -> None:
        if capacity <= 0:
            raise ValueError("event bus capacity must be positive")
        self.capacity = capacity
        self.events: list[Event] = []
        self.subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self.subscribers.append(handler)

    def emit(self, name: str, severity: str = "INFO", actor: str = "environment-core", **payload: object) -> Event:
        if severity not in SEVERITY_LEVELS:
            raise ValueError(f"unsupported severity level: {severity}")
        event = Event(name=name, severity=severity, actor=actor, payload=dict(payload), timestamp=utc_now())
        self.events.append(event)
        if len(self.events) > self.capacity:
            self.events = self.events[-self.capacity :]
        for handler in self.subscribers:
            handler(event)
        return event

    def history(self, name_prefix: str | None = None) -> list[dict]:
        selected = [event for event in self.events if name_prefix is None or event.name.startswith(name_prefix)]
        return [event.as_dict() for event in selected]

    def names(self) -> list[str]:
        return [event.name for event in self.events]
