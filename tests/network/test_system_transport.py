"""System resolver transport tests against a local UDP and TCP server."""

from __future__ import annotations

import socket

import pytest

from dns.errors import DnsTimeoutError, DnsTransportError
from dns.transport_system import SystemDnsTransport
from dns.wire import TYPE_A, parse_response
from tests.network.dns_testkit import ANSWER_ADDRESS_V4, TcpDnsServer, UdpDnsServer


def test_udp_query_returns_expected_address():
    server = UdpDnsServer().start()
    try:
        transport = SystemDnsTransport(resolvers=["127.0.0.1"], timeout=2.0, port=server.port)
        payload, latency_ms, endpoint = transport.query("example.test", TYPE_A, 4242)
        parsed = parse_response(payload)
        assert parsed["records"][0]["value"] == ANSWER_ADDRESS_V4
        assert latency_ms >= 0
        assert endpoint == f"udp://127.0.0.1:{server.port}"
        assert server.queries == ["example.test"]
    finally:
        server.stop()


def test_truncated_udp_response_triggers_tcp_fallback():
    tcp = TcpDnsServer().start()
    udp = UdpDnsServer(truncated_names={"large.example.test"}, port=tcp.port).start()
    try:
        transport = SystemDnsTransport(resolvers=["127.0.0.1"], timeout=2.0, port=tcp.port)
        payload, _, _ = transport.query("large.example.test", TYPE_A, 7)
        parsed = parse_response(payload)
        assert parsed["truncated"] is False
        assert parsed["records"][0]["value"] == ANSWER_ADDRESS_V4
        assert udp.queries == ["large.example.test"]
    finally:
        udp.stop()
        tcp.stop()


def _query_over_tcp(port: int, name: str) -> bytes:
    from dns.wire import build_query

    message = build_query(name, TYPE_A, 11)
    handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    handle.settimeout(2.0)
    handle.connect(("127.0.0.1", port))
    handle.sendall(len(message).to_bytes(2, "big") + message)
    length = int.from_bytes(handle.recv(2), "big")
    payload = b""
    while len(payload) < length:
        payload += handle.recv(length - len(payload))
    handle.close()
    return payload


def test_silent_server_produces_timeout():
    server = UdpDnsServer(silent=True).start()
    try:
        transport = SystemDnsTransport(resolvers=["127.0.0.1"], timeout=0.3, port=server.port)
        with pytest.raises(DnsTimeoutError):
            transport.query("timeout.test", TYPE_A, 1)
    finally:
        server.stop()


def test_closed_port_produces_transport_error():
    server = UdpDnsServer().start()
    port = server.port
    server.stop()
    transport = SystemDnsTransport(resolvers=["127.0.0.1"], timeout=0.3, port=port)
    with pytest.raises(DnsTimeoutError):
        transport.query("closed.test", TYPE_A, 2)


def test_endpoint_list_describes_read_only_usage():
    transport = SystemDnsTransport(resolvers=["192.0.2.1", "192.0.2.2"], port=53)
    assert transport.endpoints() == ["udp://192.0.2.1:53", "udp://192.0.2.2:53"]
