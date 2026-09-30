"""Read only system resolver transport over UDP with TCP fallback."""

from __future__ import annotations

import socket
import time

from dns.errors import DnsTimeoutError, DnsTransportError
from dns.wire import HEADER_SIZE, build_query, parse_response
from network.detection import read_resolvers

DEFAULT_SYSTEM_RESOLVER = "127.0.0.53"
MAX_UDP_MESSAGE = 4096


class SystemDnsTransport:
    """Queries the operating system resolvers without modifying any system setting."""

    protocol = "system"

    def __init__(self, resolvers: list[str] | None = None, timeout: float = 5.0, port: int = 53) -> None:
        self.resolvers = resolvers if resolvers is not None else read_resolvers() or [DEFAULT_SYSTEM_RESOLVER]
        self.timeout = timeout
        self.port = port

    def endpoints(self) -> list[str]:
        return [f"udp://{resolver}:{self.port}" for resolver in self.resolvers]

    def query(self, name: str, record_type: int, transaction_id: int) -> tuple[bytes, float, str]:
        last_error: Exception | None = None
        for resolver in self.resolvers:
            started = time.perf_counter()
            message = build_query(name, record_type, transaction_id)
            try:
                payload = self._udp_exchange(resolver, message)
            except DnsTimeoutError as error:
                last_error = error
                continue
            except OSError as error:
                last_error = DnsTransportError("system resolver transport failure", resolver=resolver, detail=str(error))
                continue
            latency_ms = (time.perf_counter() - started) * 1000.0
            parsed = parse_response(payload)
            if parsed["truncated"]:
                payload = self._tcp_exchange(resolver, message)
                latency_ms = (time.perf_counter() - started) * 1000.0
            return payload, latency_ms, f"udp://{resolver}:{self.port}"
        if last_error is None:
            raise DnsTransportError("no system resolver configured")
        raise last_error

    def _udp_exchange(self, resolver: str, message: bytes) -> bytes:
        handle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        handle.settimeout(self.timeout)
        try:
            handle.sendto(message, (resolver, self.port))
            payload, _ = handle.recvfrom(MAX_UDP_MESSAGE)
        except socket.timeout as error:
            raise DnsTimeoutError("system resolver timed out", resolver=resolver, timeout=self.timeout) from error
        finally:
            handle.close()
        if len(payload) < HEADER_SIZE:
            raise DnsTransportError("system resolver returned a short message", resolver=resolver, length=len(payload))
        return payload

    def _tcp_exchange(self, resolver: str, message: bytes) -> bytes:
        handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        handle.settimeout(self.timeout)
        try:
            handle.connect((resolver, self.port))
            handle.sendall(len(message).to_bytes(2, "big") + message)
            length_prefix = self._receive_exact(handle, 2)
            length = int.from_bytes(length_prefix, "big")
            return self._receive_exact(handle, length)
        except socket.timeout as error:
            raise DnsTimeoutError("system resolver tcp fallback timed out", resolver=resolver) from error
        finally:
            handle.close()

    def _receive_exact(self, handle: socket.socket, length: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < length:
            chunk = handle.recv(length - len(chunks))
            if not chunk:
                raise DnsTransportError("connection closed by system resolver", expected=length, received=len(chunks))
            chunks.extend(chunk)
        return bytes(chunks)
