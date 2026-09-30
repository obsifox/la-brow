"""DNS diagnostic center data model and probes."""

from __future__ import annotations

from dns.engine import DnsEngine
from dns.models import ResolverProfile


class DnsDiagnosticCenter:
    """Aggregates resolver state for the diagnostics interface."""

    def __init__(self, engine: DnsEngine, probe_name: str = "example.com") -> None:
        self.engine = engine
        self.probe_name = probe_name
        self.last_probe: dict | None = None

    def probe(self, record_type: str = "A") -> dict:
        result = self.engine.resolve(self.probe_name, record_type, use_cache=False)
        self.last_probe = {
            "query_name": result.query_name,
            "record_type": result.query_type,
            "status": "SUCCESS" if result.error is None else "FAILURE",
            "rcode": result.rcode,
            "latency_ms": round(result.latency_ms, 2),
            "records": result.records,
            "error": result.error,
            "notes": result.notes,
        }
        return self.last_probe

    def report(self, profile_source: str = "configuration") -> dict:
        status = self.engine.status()
        return {
            "active_resolver": status["active_profile"]["name"],
            "resolver_protocol": status["active_profile"]["protocol"],
            "endpoint": status["endpoint"],
            "connection_status": "UNKNOWN" if self.last_probe is None else self.last_probe["status"],
            "tls_status": "VERIFIED"
            if status["active_profile"]["protocol"] in {"doh", "dot"} and status["active_profile"]["verify_tls"]
            else "NOT_APPLICABLE",
            "dns_latency_ms": status["average_latency_ms"],
            "last_successful_query": self.engine.stats["last_success"],
            "last_error": self.engine.stats["last_error"],
            "fallback_state": status["active_profile"]["fallback_policy"],
            "profile_source": profile_source,
            "cache_entries": status["cache_entries"],
            "system_resolver_unchanged": not status["integrity"]["system_resolver_modified"],
            "last_probe": self.last_probe,
        }

    def capability_report(self, profiles: dict[str, ResolverProfile], probe: bool = False) -> dict:
        entries = []
        for profile in profiles.values():
            entry = {"id": profile.id, "protocol": profile.protocol.value, "supported": True}
            if probe and profile.protocol.value in {"doh", "dot"}:
                engine = DnsEngine(profile)
                result = engine.resolve(self.probe_name, "A", use_cache=False)
                entry["probe"] = {
                    "status": "SUCCESS" if result.error is None else "FAILURE",
                    "latency_ms": round(result.latency_ms, 2),
                    "error": result.error,
                    "records": result.records,
                }
            entries.append(entry)
        return {"profiles": entries}
