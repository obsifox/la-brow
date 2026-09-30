"""Value objects for DNS resolution and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ResolverProtocol(str, Enum):
    SYSTEM = "system"
    CUSTOM = "custom"
    DOH = "doh"
    DOT = "dot"


class FallbackPolicy(str, Enum):
    NEVER = "never"
    EXPLICIT = "explicit"
    SYSTEM_ON_FAILURE = "system_on_failure"


@dataclass(frozen=True)
class ResolverProfile:
    id: str
    name: str
    protocol: ResolverProtocol
    endpoint: str | None = None
    hostname: str | None = None
    port: int | None = None
    bootstrap_addresses: tuple[str, ...] = ()
    verify_tls: bool = True
    timeout_seconds: float = 5.0
    fallback_policy: FallbackPolicy = FallbackPolicy.NEVER
    privacy_note: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "protocol": self.protocol.value,
            "endpoint": self.endpoint,
            "hostname": self.hostname,
            "port": self.port,
            "bootstrap_addresses": list(self.bootstrap_addresses),
            "verify_tls": self.verify_tls,
            "timeout_seconds": self.timeout_seconds,
            "fallback_policy": self.fallback_policy.value,
            "privacy_note": self.privacy_note,
        }


@dataclass
class ResolutionResult:
    query_name: str
    query_type: str
    protocol: str
    resolver_id: str
    endpoint: str
    records: list[dict]
    rcode: str
    latency_ms: float
    tls_verified: bool
    fallback_used: bool
    cache_hit: bool
    timestamp: str
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    def addresses(self) -> list[str]:
        return [record["value"] for record in self.records if record["type"] in {"A", "AAAA"}]

    def as_dict(self) -> dict:
        return {
            "query_name": self.query_name,
            "query_type": self.query_type,
            "protocol": self.protocol,
            "resolver_id": self.resolver_id,
            "endpoint": self.endpoint,
            "records": self.records,
            "rcode": self.rcode,
            "latency_ms": round(self.latency_ms, 2),
            "tls_verified": self.tls_verified,
            "fallback_used": self.fallback_used,
            "cache_hit": self.cache_hit,
            "timestamp": self.timestamp,
            "error": self.error,
            "notes": list(self.notes),
        }
