"""DNS over TLS and DNS over HTTPS client tests against local TLS servers."""

from __future__ import annotations

import pytest

from dns.errors import DnsTlsError, DnsTransportError
from dns.models import ResolverProfile, ResolverProtocol
from dns.wire import TYPE_A, parse_response
from dot.client import DotClient
from doh.client import DohClient
from tests.network.dns_testkit import ANSWER_ADDRESS_V4, DohServer, TlsDnsServer, generate_certificate, trusted_context

CERT_DIRECTORY = "/tmp/la-brow-test-certs"


@pytest.fixture(scope="module")
def certificate():
    return generate_certificate(__import__("pathlib").Path(CERT_DIRECTORY))


def dot_profile(port: int) -> ResolverProfile:
    return ResolverProfile(
        id="local-dot",
        name="Local DNS over TLS",
        protocol=ResolverProtocol.DOT,
        hostname="localhost",
        port=port,
        bootstrap_addresses=("127.0.0.1",),
    )


def doh_profile(port: int) -> ResolverProfile:
    return ResolverProfile(
        id="local-doh",
        name="Local DNS over HTTPS",
        protocol=ResolverProtocol.DOH,
        endpoint=f"https://localhost:{port}/dns-query",
        bootstrap_addresses=("127.0.0.1",),
    )


def test_dot_query_succeeds_with_trusted_certificate(certificate):
    cert_path, key_path = certificate
    server = TlsDnsServer(cert_path, key_path).start()
    try:
        client = DotClient(dot_profile(server.port), context=trusted_context(cert_path))
        payload, latency_ms, endpoint = client.query("example.test", TYPE_A, 99)
        parsed = parse_response(payload)
        assert parsed["records"][0]["value"] == ANSWER_ADDRESS_V4
        assert latency_ms >= 0
        assert endpoint == f"tls://localhost:{server.port}"
    finally:
        server.stop()


def test_dot_rejects_untrusted_certificate(certificate):
    cert_path, key_path = certificate
    server = TlsDnsServer(cert_path, key_path).start()
    try:
        client = DotClient(dot_profile(server.port))
        with pytest.raises(DnsTlsError):
            client.query("example.test", TYPE_A, 5)
    finally:
        server.stop()


def test_dot_requires_hostname_profile():
    with pytest.raises(DnsTransportError):
        DotClient(ResolverProfile(id="bad", name="bad", protocol=ResolverProtocol.DOT))


def test_dot_rejects_wrong_protocol_profile():
    with pytest.raises(DnsTransportError):
        DotClient(ResolverProfile(id="bad", name="bad", protocol=ResolverProtocol.DOH, endpoint="https://example.test/dns-query"))


def test_doh_query_succeeds_with_trusted_certificate(certificate):
    cert_path, key_path = certificate
    server = DohServer(cert_path, key_path).start()
    try:
        client = DohClient(doh_profile(server.port), context=trusted_context(cert_path))
        payload, latency_ms, endpoint = client.query("example.test", TYPE_A, 77)
        parsed = parse_response(payload)
        assert parsed["records"][0]["value"] == ANSWER_ADDRESS_V4
        assert endpoint == f"https://localhost:{server.port}/dns-query"
    finally:
        server.stop()


def test_doh_rejects_untrusted_certificate(certificate):
    cert_path, key_path = certificate
    server = DohServer(cert_path, key_path).start()
    try:
        client = DohClient(doh_profile(server.port))
        with pytest.raises(DnsTlsError):
            client.query("example.test", TYPE_A, 5)
    finally:
        server.stop()


def test_doh_rejects_wrong_content_type(certificate):
    cert_path, key_path = certificate
    server = DohServer(cert_path, key_path, content_type="application/json").start()
    try:
        client = DohClient(doh_profile(server.port), context=trusted_context(cert_path))
        with pytest.raises(DnsTransportError):
            client.query("example.test", TYPE_A, 5)
    finally:
        server.stop()


def test_doh_rejects_error_status(certificate):
    cert_path, key_path = certificate
    server = DohServer(cert_path, key_path, status_code=502).start()
    try:
        client = DohClient(doh_profile(server.port), context=trusted_context(cert_path))
        with pytest.raises(DnsTransportError):
            client.query("example.test", TYPE_A, 5)
    finally:
        server.stop()


def test_doh_endpoint_description():
    client = DohClient(ResolverProfile(id="p", name="p", protocol=ResolverProtocol.DOH, endpoint="https://resolver.test/dns-query"))
    assert client.endpoint_description() == "https://resolver.test/dns-query"
