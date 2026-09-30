"""DNS wire format tests."""

from __future__ import annotations

import struct

import pytest

from dns.errors import DnsDecodingError, DnsEncodingError
from dns.wire import (
    HEADER_SIZE,
    TYPE_A,
    TYPE_AAAA,
    TYPE_CNAME,
    TYPE_MX,
    TYPE_TXT,
    build_query,
    decode_name,
    encode_name,
    min_ttl,
    parse_response,
)


def build_response(question_name: str, answers: list[tuple[str, int, int, bytes]], rcode: int = 0) -> bytes:
    header = struct.pack("!HHHHHH", 0x1234, 0x8180 | rcode, 1, len(answers), 0, 0)
    body = encode_name(question_name) + struct.pack("!HH", TYPE_A, 1)
    for name, record_type, ttl, payload in answers:
        body += encode_name(name) + struct.pack("!HHIH", record_type, 1, ttl, len(payload)) + payload
    return header + body


def test_encode_name_simple_and_trailing_dot():
    assert encode_name("example.com") == b"\x07example\x03com\x00"
    assert encode_name("example.com.") == b"\x07example\x03com\x00"


def test_encode_name_rejects_long_label():
    with pytest.raises(DnsEncodingError):
        encode_name("a" * 70 + ".com")


def test_query_structure():
    message = build_query("example.com", TYPE_A, 0x4242)
    assert len(message) > HEADER_SIZE
    transaction_id, flags, question_count = struct.unpack("!HHH", message[:6])
    assert transaction_id == 0x4242
    assert flags & 0x0100
    assert question_count == 1


def test_transaction_id_bounds():
    with pytest.raises(DnsEncodingError):
        build_query("example.com", TYPE_A, 70000)


def test_decode_name_follows_compression_pointer():
    message = encode_name("example.com") + b"\xc0\x00"
    name, position = decode_name(message, len(encode_name("example.com")))
    assert name == "example.com"
    assert position == len(message)


def test_decode_name_detects_pointer_loop():
    message = b"\xc0\x00"
    with pytest.raises(DnsDecodingError):
        decode_name(message, 0)


def test_parse_a_record():
    payload = bytes([93, 184, 216, 34])
    parsed = parse_response(build_response("example.com", [("example.com", TYPE_A, 300, payload)]))
    assert parsed["rcode_name"] == "NOERROR"
    assert parsed["records"][0]["value"] == "93.184.216.34"
    assert parsed["records"][0]["ttl"] == 300


def test_parse_aaaa_record():
    payload = bytes.fromhex("26064700000000000000000068104210")
    parsed = parse_response(build_response("example.com", [("example.com", TYPE_AAAA, 120, payload)]))
    assert parsed["records"][0]["type"] == "AAAA"
    assert parsed["records"][0]["value"] == "2606:4700::6810:4210"


def test_parse_cname_mx_and_txt_records():
    cname_payload = encode_name("target.example.com")
    mx_payload = struct.pack("!H", 10) + encode_name("mail.example.com")
    txt_payload = b"\x0bhello world"
    parsed = parse_response(
        build_response(
            "example.com",
            [
                ("example.com", TYPE_CNAME, 60, cname_payload),
                ("example.com", TYPE_MX, 60, mx_payload),
                ("example.com", TYPE_TXT, 60, txt_payload),
            ],
        )
    )
    types = {record["type"] for record in parsed["records"]}
    assert {"CNAME", "MX", "TXT"} <= types
    mx = next(record for record in parsed["records"] if record["type"] == "MX")
    assert mx["value"]["exchange"] == "mail.example.com"
    txt = next(record for record in parsed["records"] if record["type"] == "TXT")
    assert txt["value"] == ["hello world"]


def test_error_response_code_is_exposed():
    parsed = parse_response(build_response("example.com", [], rcode=3))
    assert parsed["rcode_name"] == "NXDOMAIN"


def test_truncation_flag_is_exposed():
    header = struct.pack("!HHHHHH", 1, 0x8380, 1, 0, 0, 0)
    body = encode_name("example.com") + struct.pack("!HH", TYPE_A, 1)
    assert parse_response(header + body)["truncated"] is True


def test_min_ttl_uses_lowest_non_zero_value():
    payload = bytes([93, 184, 216, 34])
    parsed = parse_response(build_response("example.com", [("example.com", TYPE_A, 900, payload)]))
    assert min_ttl(parsed) == 900


def test_short_message_is_rejected():
    with pytest.raises(DnsDecodingError):
        parse_response(b"\x00\x01")
