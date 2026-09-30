"""Structured event bus tests."""

from __future__ import annotations

from geo.events import EventBus, redact_payload


def test_event_history_is_bounded():
    bus = EventBus(capacity=4)
    for index in range(10):
        bus.emit("geo.changed", actor="test", index=index)
    assert len(bus.events) == 4
    assert bus.events[-1].payload["index"] == 9


def test_invalid_severity_is_rejected():
    bus = EventBus()
    bus.emit("geo.changed", severity="INFO")
    try:
        bus.emit("geo.changed", severity="LOUD")
    except ValueError as error:
        assert "unsupported severity" in str(error)
    else:
        raise AssertionError("invalid severity must raise")


def test_sensitive_payload_keys_are_redacted():
    payload = redact_payload({"api_token": "abc", "nested": {"password": "x"}, "zone": "Europe/Berlin"})
    assert payload["api_token"] == "[redacted]"
    assert payload["nested"]["password"] == "[redacted]"
    assert payload["zone"] == "Europe/Berlin"


def test_subscribers_receive_events_in_order():
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe(lambda event: seen.append(event.name))
    bus.emit("network.changed")
    bus.emit("dns.changed")
    assert seen == ["network.changed", "dns.changed"]
    assert bus.names() == ["network.changed", "dns.changed"]
