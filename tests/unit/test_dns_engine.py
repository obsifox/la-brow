"""DNS engine tests using a deterministic in-process resolver."""

from __future__ import annotations

import struct

import pytest

from dns.engine import DnsEngine, snapshot_system_resolver
from dns.errors import DnsTimeoutError
from dns.models import FallbackPolicy, ResolverProfile, ResolverProtocol
from dns.wire import TYPE_A, TYPE_AAAA, build_query, encode_name, parse_response


def build_answer(name: str, record_type: int, value: bytes, ttl: int = 60, transaction_id: int = 1) -> bytes:
    header = struct.pack("!HHHHHH", transaction_id, 0x8180, 1, 1, 0, 0)
    body = encode_name(name) + struct.pack("!HH", record_type, 1)
    body += encode_name(name) + struct.pack("!HHIH", record_type, 1, ttl, len(value)) + value
    return header + body


class StubTransport:
    protocol = "stub"

    def __init__(self, payload: bytes | None = None, failure: Exception | None = None, latency_ms: float = 1.0) -> None:
        self.payload = payload
        self.failure = failure
        self.latency_ms = latency_ms
        self.calls = 0

    def query(self, name: str, record_type: int, transaction_id: int):
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        payload = self.payload or build_answer(name, record_type, bytes([93, 184, 216, 34]), transaction_id=transaction_id)
        return payload, self.latency_ms, "stub://resolver"


def profile(protocol: ResolverProtocol = ResolverProtocol.DOH, fallback: FallbackPolicy = FallbackPolicy.NEVER, profile_id: str = "test") -> ResolverProfile:
    return ResolverProfile(id=profile_id, name="Test Resolver", protocol=protocol, endpoint="https://resolver.test/dns-query", fallback_policy=fallback)


def test_successful_resolution_records_diagnostics():
    engine = DnsEngine(profile())
    engine.transports["test"] = StubTransport(latency_ms=12.5)
    result = engine.resolve("example.com", "A")
    assert result.rcode == "NOERROR"
    assert result.records[0]["value"] == "93.184.216.34"
    assert result.latency_ms == 12.5
    assert engine.status()["stats"]["queries"] == 1
    assert engine.status()["stats"]["last_success"]["query_name"] == "example.com"


def test_cache_is_used_for_repeated_queries():
    engine = DnsEngine(profile())
    transport = StubTransport()
    engine.transports["test"] = transport
    engine.resolve("example.com", "A")
    cached = engine.resolve("example.com", "A")
    assert cached.cache_hit is True
    assert transport.calls == 1


def test_cache_can_be_bypassed():
    engine = DnsEngine(profile())
    transport = StubTransport()
    engine.transports["test"] = transport
    engine.resolve("example.com", "A")
    engine.resolve("example.com", "A", use_cache=False)
    assert transport.calls == 2


def test_failure_without_fallback_is_reported():
    engine = DnsEngine(profile(fallback=FallbackPolicy.NEVER))
    engine.transports["test"] = StubTransport(failure=DnsTimeoutError("timeout"))
    result = engine.resolve("example.com", "A")
    assert result.rcode == "FAILURE"
    assert result.error == "dns_timeout"
    assert result.fallback_used is False
    assert result.notes[-1].startswith("fallback policy is never")
    assert engine.status()["stats"]["failures"] == 1


def test_explicit_fallback_uses_registered_profile():
    primary = profile(profile_id="primary", fallback=FallbackPolicy.SYSTEM_ON_FAILURE)
    secondary = ResolverProfile(id="system", name="System", protocol=ResolverProtocol.SYSTEM, fallback_policy=FallbackPolicy.NEVER)
    engine = DnsEngine(primary, fallback_profile=secondary)
    engine.transports["primary"] = StubTransport(failure=DnsTimeoutError("timeout"))
    engine.transports["system"] = StubTransport()
    result = engine.resolve("example.com", "A")
    assert result.fallback_used is True
    assert result.records
    assert any(note.startswith("fallback used after failure") for note in result.notes)
    assert engine.status()["stats"]["fallbacks"] == 1


def test_unsupported_record_type_is_rejected():
    engine = DnsEngine(profile())
    try:
        engine.resolve("example.com", "LOC")
    except Exception as error:
        assert getattr(error, "code", "") == "dns_policy_error"
    else:
        raise AssertionError("unsupported record type must raise")


def test_resolver_integrity_check_reports_system_state():
    engine = DnsEngine(profile())
    integrity = engine.integrity_check()
    assert "system_resolver_modified" in integrity
    assert integrity["before"]["path"] == str(snapshot_system_resolver()["path"])
    assert integrity["statement"].startswith("browser scoped DNS")


def test_record_type_specific_filtering():
    engine = DnsEngine(profile())
    engine.transports["test"] = StubTransport(payload=build_answer("example.com", TYPE_AAAA, bytes.fromhex("26064700000000000000000068104210")))
    result = engine.resolve("example.com", "AAAA")
    assert result.records[0]["type"] == "AAAA"
    assert result.records[0]["value"] == "2606:4700::6810:4210"
