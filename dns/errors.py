"""Structured errors for the DNS subsystem."""

from __future__ import annotations


class DnsError(Exception):
    code = "dns_error"

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


class DnsEncodingError(DnsError):
    code = "dns_encoding_error"


class DnsDecodingError(DnsError):
    code = "dns_decoding_error"


class DnsTimeoutError(DnsError):
    code = "dns_timeout"


class DnsTransportError(DnsError):
    code = "dns_transport_error"


class DnsTlsError(DnsError):
    code = "dns_tls_error"


class DnsResponseCodeError(DnsError):
    code = "dns_response_code_error"


class DnsPolicyError(DnsError):
    code = "dns_policy_error"
