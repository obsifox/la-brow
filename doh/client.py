"""DNS over HTTPS transport using RFC 8484 message format over HTTP POST."""

from __future__ import annotations

import http.client
import socket
import ssl
import time
from urllib.parse import urlsplit

from dns.errors import DnsTimeoutError, DnsTlsError, DnsTransportError
from dns.models import ResolverProfile
from dns.wire import build_query, parse_response

DOH_MEDIA_TYPE = "application/dns-message"
MAX_RESPONSE_BYTES = 65535


class DohClient:
    """Browser scoped DNS over HTTPS resolver with explicit TLS validation."""

    protocol = "doh"

    def __init__(self, profile: ResolverProfile, context: ssl.SSLContext | None = None) -> None:
        if profile.protocol.value != "doh":
            raise DnsTransportError("profile is not a DNS over HTTPS profile", resolver=profile.id)
        if not profile.endpoint:
            raise DnsTransportError("DNS over HTTPS profile requires an endpoint", resolver=profile.id)
        self.profile = profile
        self.endpoint = profile.endpoint
        self.parts = urlsplit(profile.endpoint)
        self.context = context or ssl.create_default_context()
        if not profile.verify_tls:
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE

    def endpoint_description(self) -> str:
        return self.endpoint

    def query(self, name: str, record_type: int, transaction_id: int) -> tuple[bytes, float, str]:
        message = build_query(name, record_type, transaction_id)
        host = self.parts.hostname
        if host is None:
            raise DnsTransportError("DNS over HTTPS endpoint has no host", endpoint=self.endpoint)
        port = self.parts.port or (443 if self.parts.scheme == "https" else 80)
        connect_host = host
        if self.profile.bootstrap_addresses:
            connect_host = self.profile.bootstrap_addresses[0]
        started = time.perf_counter()
        try:
            if self.parts.scheme == "https":
                raw = socket.create_connection((connect_host, port), timeout=self.profile.timeout_seconds)
                try:
                    wrapped = self.context.wrap_socket(raw, server_hostname=host)
                except ssl.SSLError as error:
                    raw.close()
                    raise DnsTlsError(
                        "DNS over HTTPS TLS handshake failed",
                        endpoint=self.endpoint,
                        detail=str(error),
                    ) from error
                connection = http.client.HTTPConnection(host, port, timeout=self.profile.timeout_seconds)
                connection.sock = wrapped
            else:
                connection = http.client.HTTPConnection(host, port, timeout=self.profile.timeout_seconds)
            headers = {"Content-Type": DOH_MEDIA_TYPE, "Accept": DOH_MEDIA_TYPE}
            connection.request("POST", self.parts.path or "/dns-query", body=message, headers=headers)
            response = connection.getresponse()
            payload = response.read(MAX_RESPONSE_BYTES)
            status = response.status
            content_type = response.getheader("Content-Type", "")
            connection.close()
        except socket.timeout as error:
            raise DnsTimeoutError(
                "DNS over HTTPS request timed out",
                endpoint=self.endpoint,
                timeout=self.profile.timeout_seconds,
            ) from error
        except (ssl.SSLError, DnsTlsError):
            raise
        except OSError as error:
            raise DnsTransportError("DNS over HTTPS transport failure", endpoint=self.endpoint, detail=str(error)) from error
        latency_ms = (time.perf_counter() - started) * 1000.0
        if status != 200:
            raise DnsTransportError("DNS over HTTPS endpoint returned an error status", status=status, endpoint=self.endpoint)
        if DOH_MEDIA_TYPE not in content_type:
            raise DnsTransportError(
                "DNS over HTTPS endpoint returned an unexpected content type",
                content_type=content_type,
                endpoint=self.endpoint,
            )
        parsed = parse_response(payload)
        if parsed["transaction_id"] != transaction_id:
            raise DnsTransportError("DNS over HTTPS transaction id mismatch", endpoint=self.endpoint)
        return payload, latency_ms, self.endpoint
