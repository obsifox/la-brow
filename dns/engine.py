"""Browser scoped DNS engine with explicit fallback and operating system isolation."""

from __future__ import annotations

import hashlib
import random
import time
from datetime import datetime, timezone as timezone_module
from pathlib import Path

import yaml

from dns.errors import DnsError, DnsPolicyError, DnsResponseCodeError
from dns.models import FallbackPolicy, ResolutionResult, ResolverProfile, ResolverProtocol
from dns.transport_system import SystemDnsTransport
from dns.wire import TYPE_NAMES, min_ttl, parse_response

PROVIDER_CONFIG_PATH = "config/network/dns-providers.yaml"
RESOLV_CONF = Path("/etc/resolv.conf")
PROTOCOL_BY_TYPE = {name: code for code, name in TYPE_NAMES.items()}
CACHE_MAX_ENTRIES = 512


def snapshot_system_resolver() -> dict:
    entry = {"path": str(RESOLV_CONF), "present": RESOLV_CONF.is_file(), "sha256": None}
    if entry["present"]:
        try:
            entry["sha256"] = hashlib.sha256(RESOLV_CONF.read_bytes()).hexdigest()
        except OSError:
            entry["sha256"] = None
    return entry


def load_provider_profiles(repo: Path) -> dict[str, ResolverProfile]:
    payload = yaml.safe_load((repo / PROVIDER_CONFIG_PATH).read_text(encoding="utf-8"))
    profiles: dict[str, ResolverProfile] = {}
    for entry in payload.get("providers", []):
        profile = ResolverProfile(
            id=entry["id"],
            name=entry["name"],
            protocol=ResolverProtocol(entry["protocol"]),
            endpoint=entry.get("endpoint"),
            hostname=entry.get("hostname"),
            port=entry.get("port"),
            bootstrap_addresses=tuple(entry.get("bootstrap_addresses", [])),
            timeout_seconds=float(entry.get("timeout_seconds", 5.0)),
            fallback_policy=FallbackPolicy(entry.get("fallback_policy", "never")),
            privacy_note=entry.get("privacy_note", ""),
        )
        profiles[profile.id] = profile
    return profiles


class DnsEngine:
    """Resolves names through a single active profile and records observable diagnostics."""

    def __init__(
        self,
        profile: ResolverProfile,
        fallback_profile: ResolverProfile | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.profile = profile
        self.fallback_profile = fallback_profile
        self.timeout_seconds = timeout_seconds
        self.cache: dict[tuple, tuple[float, dict]] = {}
        self.transaction_counter = random.randint(1, 0xFFFF)
        self.stats = {
            "queries": 0,
            "cache_hits": 0,
            "failures": 0,
            "fallbacks": 0,
            "latency_ms_total": 0.0,
            "last_success": None,
            "last_error": None,
        }
        self.system_snapshot = snapshot_system_resolver()
        self.transports: dict[str, object] = {}
        self.transport_overrides: dict[str, object] = {}

    def register_transport(self, profile_id: str, transport: object) -> None:
        self.transport_overrides[profile_id] = transport

    def _next_transaction_id(self) -> int:
        self.transaction_counter = (self.transaction_counter + 1) % 0xFFFF or 1
        return self.transaction_counter

    def transport_for(self, profile: ResolverProfile):
        key = profile.id
        if key in self.transport_overrides:
            return self.transport_overrides[key]
        if key in self.transports:
            return self.transports[key]
        if profile.protocol is ResolverProtocol.DOH:
            from doh.client import DohClient

            transport = DohClient(profile)
        elif profile.protocol is ResolverProtocol.DOT:
            from dot.client import DotClient

            transport = DotClient(profile)
        else:
            transport = SystemDnsTransport(timeout=self.timeout_seconds or profile.timeout_seconds)
        self.transports[key] = transport
        return transport

    def resolve(self, name: str, record_type: str = "A", use_cache: bool = True) -> ResolutionResult:
        if record_type not in PROTOCOL_BY_TYPE:
            raise DnsPolicyError("unsupported record type", record_type=record_type, supported=sorted(PROTOCOL_BY_TYPE))
        type_code = PROTOCOL_BY_TYPE[record_type]
        cache_key = (self.profile.id, name.lower(), record_type)
        now = time.time()
        if use_cache and cache_key in self.cache:
            expires_at, parsed = self.cache[cache_key]
            if expires_at > now:
                self.stats["queries"] += 1
                self.stats["cache_hits"] += 1
                return self._result(parsed, name, record_type, 0.0, cache_hit=True, endpoint=self.endpoint_label(), fallback_used=False)
        self.stats["queries"] += 1
        try:
            return self._resolve_once(name, record_type, type_code, cache_key)
        except DnsError as primary_error:
            self.stats["failures"] += 1
            self.stats["last_error"] = {
                "code": getattr(primary_error, "code", "dns_error"),
                "message": primary_error.message,
                "at": datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            return self._handle_failure(name, record_type, type_code, primary_error)

    def _resolve_once(self, name: str, record_type: str, type_code: int, cache_key: tuple) -> ResolutionResult:
        transport = self.transport_for(self.profile)
        payload, latency_ms, endpoint = transport.query(name, type_code, self._next_transaction_id())
        parsed = parse_response(payload)
        if parsed["rcode"] != 0:
            raise DnsResponseCodeError(
                "resolver returned an error response code",
                rcode=parsed["rcode_name"],
                query_name=name,
                record_type=record_type,
            )
        ttl = min_ttl(parsed)
        self.cache[cache_key] = (time.time() + ttl, parsed)
        if len(self.cache) > CACHE_MAX_ENTRIES:
            oldest = min(self.cache, key=lambda key: self.cache[key][0])
            self.cache.pop(oldest, None)
        self.stats["latency_ms_total"] += latency_ms
        self.stats["last_success"] = {
            "query_name": name,
            "record_type": record_type,
            "at": datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "protocol": self.profile.protocol.value,
        }
        return self._result(parsed, name, record_type, latency_ms, cache_hit=False, endpoint=endpoint, fallback_used=False)

    def _handle_failure(self, name: str, record_type: str, type_code: int, primary_error: DnsError) -> ResolutionResult:
        policy = self.profile.fallback_policy
        if policy is FallbackPolicy.SYSTEM_ON_FAILURE and self.fallback_profile is not None:
            self.stats["fallbacks"] += 1
            transport = self.transport_for(self.fallback_profile)
            payload, latency_ms, endpoint = transport.query(name, type_code, self._next_transaction_id())
            parsed = parse_response(payload)
            result = self._result(parsed, name, record_type, latency_ms, cache_hit=False, endpoint=endpoint, fallback_used=True)
            result.notes.append(f"fallback used after failure: {primary_error.code}")
            result.notes.append("fallback was explicitly configured by the active resolver profile")
            return result
        return ResolutionResult(
            query_name=name,
            query_type=record_type,
            protocol=self.profile.protocol.value,
            resolver_id=self.profile.id,
            endpoint=self.profile.endpoint or self.profile.hostname or "system",
            records=[],
            rcode="FAILURE",
            latency_ms=0.0,
            tls_verified=self.profile.verify_tls,
            fallback_used=False,
            cache_hit=False,
            timestamp=datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            error=primary_error.code,
            notes=[primary_error.message, "fallback policy is never, so the failure is reported without substitution"],
        )

    def _result(
        self,
        parsed: dict,
        name: str,
        record_type: str,
        latency_ms: float,
        cache_hit: bool,
        endpoint: str,
        fallback_used: bool,
    ) -> ResolutionResult:
        records = [record for record in parsed["records"] if record["type"] == record_type]
        if not records:
            records = parsed["records"]
        return ResolutionResult(
            query_name=name,
            query_type=record_type,
            protocol=self.profile.protocol.value,
            resolver_id=self.profile.id,
            endpoint=endpoint,
            records=records,
            rcode=parsed["rcode_name"],
            latency_ms=latency_ms,
            tls_verified=self.profile.verify_tls and self.profile.protocol in {ResolverProtocol.DOH, ResolverProtocol.DOT},
            fallback_used=fallback_used,
            cache_hit=cache_hit,
            timestamp=datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def endpoint_label(self) -> str:
        if self.profile.protocol is ResolverProtocol.DOH:
            return self.profile.endpoint or "unset"
        if self.profile.protocol is ResolverProtocol.DOT:
            return f"tls://{self.profile.hostname}:{self.profile.port or 853}"
        return "udp://system:53"

    def integrity_check(self) -> dict:
        current = snapshot_system_resolver()
        unchanged = current == self.system_snapshot
        return {
            "system_resolver_modified": not unchanged,
            "before": self.system_snapshot,
            "after": current,
            "statement": "browser scoped DNS must not modify operating system resolver configuration",
        }

    def average_latency_ms(self) -> float:
        resolved = self.stats["queries"] - self.stats["cache_hits"]
        if resolved <= 0:
            return 0.0
        return self.stats["latency_ms_total"] / resolved

    def status(self) -> dict:
        return {
            "active_profile": self.profile.as_dict(),
            "endpoint": self.endpoint_label(),
            "average_latency_ms": round(self.average_latency_ms(), 2),
            "stats": dict(self.stats),
            "cache_entries": len(self.cache),
            "integrity": self.integrity_check(),
        }
