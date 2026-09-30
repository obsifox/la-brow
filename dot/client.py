"""DNS over TLS transport with strict certificate validation."""

from __future__ import annotations

import socket
import ssl
import time

from dns.errors import DnsTimeoutError, DnsTlsError, DnsTransportError
from dns.models import ResolverProfile
from dns.wire import build_query, parse_response

DOT_PORT = 853


class DotClient:
    """Browser scoped DNS over TLS resolver that never changes system settings."""

    protocol = "dot"

    def __init__(self, profile: ResolverProfile, context: ssl.SSLContext | None = None) -> None:
        if profile.protocol.value != "dot":
            raise DnsTransportError("profile is not a DNS over TLS profile", resolver=profile.id)
        if not profile.hostname:
            raise DnsTransportError("DNS over TLS profile requires a hostname", resolver=profile.id)
        self.profile = profile
        self.hostname = profile.hostname
        self.port = profile.port or DOT_PORT
        self.context = context or ssl.create_default_context()
        if not profile.verify_tls:
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE

    def endpoint_description(self) -> str:
        return f"tls://{self.hostname}:{self.port}"

    def query(self, name: str, record_type: int, transaction_id: int) -> tuple[bytes, float, str]:
        target = self.profile.bootstrap_addresses[0] if self.profile.bootstrap_addresses else self.hostname
        started = time.perf_counter()
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(self.profile.timeout_seconds)
        try:
            raw.connect((target, self.port))
        except socket.timeout as error:
            raw.close()
            raise DnsTimeoutError("DNS over TLS connection timed out", hostname=self.hostname, port=self.port) from error
        except OSError as error:
            raw.close()
            raise DnsTransportError("DNS over TLS connection failed", hostname=self.hostname, port=self.port, detail=str(error)) from error
        try:
            wrapped = self.context.wrap_socket(raw, server_hostname=self.hostname)
            verified = wrapped.getpeercert() not in (None, {})
        except ssl.SSLError as error:
            raw.close()
            raise DnsTlsError("DNS over TLS handshake failed", hostname=self.hostname, detail=str(error)) from error
        message = build_query(name, record_type, transaction_id)
        try:
            wrapped.sendall(len(message).to_bytes(2, "big") + message)
            length = int.from_bytes(self._receive_exact(wrapped, 2), "big")
            payload = self._receive_exact(wrapped, length)
        except socket.timeout as error:
            raise DnsTimeoutError("DNS over TLS query timed out", hostname=self.hostname) from error
        except OSError as error:
            raise DnsTransportError("DNS over TLS exchange failed", hostname=self.hostname, detail=str(error)) from error
        finally:
            wrapped.close()
        latency_ms = (time.perf_counter() - started) * 1000.0
        parsed = parse_response(payload)
        if parsed["transaction_id"] != transaction_id:
            raise DnsTransportError("DNS over TLS transaction id mismatch", hostname=self.hostname)
        if not verified and self.profile.verify_tls:
            raise DnsTlsError("DNS over TLS peer certificate could not be verified", hostname=self.hostname)
        return payload, latency_ms, self.endpoint_description()

    def _receive_exact(self, handle: ssl.SSLSocket, length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            chunk = handle.recv(length - len(chunks))
            if not chunk:
                raise DnsTransportError("connection closed by DNS over TLS peer", expected=length, received=len(chunks))
            chunks.extend(chunk)
        return bytes(chunks)
