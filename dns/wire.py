"""DNS message encoding and decoding for the record types supported by the resolver."""

from __future__ import annotations

import ipaddress
import struct

from dns.errors import DnsDecodingError, DnsEncodingError

MAX_LABEL_LENGTH = 63
MAX_NAME_LENGTH = 255
MAX_MESSAGE_LENGTH = 65535
HEADER_FORMAT = "!HHHHHH"
HEADER_SIZE = 12

TYPE_A = 1
TYPE_NS = 2
TYPE_CNAME = 5
TYPE_SOA = 6
TYPE_PTR = 12
TYPE_MX = 15
TYPE_TXT = 16
TYPE_AAAA = 28
TYPE_SRV = 33
TYPE_HTTPS = 65
TYPE_ANY = 255

CLASS_IN = 1

TYPE_NAMES = {
    TYPE_A: "A",
    TYPE_NS: "NS",
    TYPE_CNAME: "CNAME",
    TYPE_SOA: "SOA",
    TYPE_PTR: "PTR",
    TYPE_MX: "MX",
    TYPE_TXT: "TXT",
    TYPE_AAAA: "AAAA",
    TYPE_SRV: "SRV",
    TYPE_HTTPS: "HTTPS",
    TYPE_ANY: "ANY",
}

NAME_TYPES = {TYPE_NS, TYPE_CNAME, TYPE_PTR}

RCODE_NAMES = {
    0: "NOERROR",
    1: "FORMERR",
    2: "SERVFAIL",
    3: "NXDOMAIN",
    4: "NOTIMP",
    5: "REFUSED",
}


def encode_name(name: str) -> bytes:
    trimmed = name.rstrip(".")
    if trimmed == "":
        return b"\x00"
    label_bytes = []
    total = 0
    for label in trimmed.split("."):
        if not label:
            raise DnsEncodingError("empty label in name", name=name)
        encoded = label.encode("idna") if any(ord(character) > 127 for character in label) else label.encode("ascii")
        if len(encoded) > MAX_LABEL_LENGTH:
            raise DnsEncodingError("label exceeds maximum length", label=label)
        label_bytes.append(bytes([len(encoded)]) + encoded)
        total += len(encoded) + 1
    if total + 1 > MAX_NAME_LENGTH:
        raise DnsEncodingError("name exceeds maximum length", name=name)
    return b"".join(label_bytes) + b"\x00"


def decode_name(message: bytes, offset: int, depth: int = 0) -> tuple[str, int]:
    if depth > 32:
        raise DnsDecodingError("compression pointer loop detected")
    labels: list[str] = []
    position = offset
    consumed = None
    while True:
        if position >= len(message):
            raise DnsDecodingError("name extends past message end")
        length = message[position]
        if length == 0:
            position += 1
            break
        if length & 0xC0 == 0xC0:
            if position + 1 >= len(message):
                raise DnsDecodingError("truncated compression pointer")
            pointer = ((length & 0x3F) << 8) | message[position + 1]
            if consumed is None:
                consumed = position + 2
            nested, _ = decode_name(message, pointer, depth + 1)
            labels.append(nested)
            position += 2
            break
        position += 1
        label = message[position : position + length]
        if len(label) != length:
            raise DnsDecodingError("truncated label")
        labels.append(label.decode("ascii", errors="replace"))
        position += length
    return ".".join(part for part in labels if part), (consumed if consumed is not None else position)


def build_query(name: str, record_type: int, transaction_id: int, recursion_desired: bool = True) -> bytes:
    if not 0 <= transaction_id <= 0xFFFF:
        raise DnsEncodingError("transaction id out of range", transaction_id=transaction_id)
    flags = 0x0100 if recursion_desired else 0x0000
    header = struct.pack(HEADER_FORMAT, transaction_id, flags, 1, 0, 0, 0)
    question = encode_name(name) + struct.pack("!HH", record_type, CLASS_IN)
    message = header + question
    if len(message) > MAX_MESSAGE_LENGTH:
        raise DnsEncodingError("encoded query exceeds maximum length")
    return message


def _decode_character_strings(payload: bytes, start: int, end: int) -> list[str]:
    strings: list[str] = []
    position = start
    while position < end:
        length = payload[position]
        position += 1
        strings.append(payload[position : position + length].decode("utf-8", errors="replace"))
        position += length
    return strings


def _decode_rdata(message: bytes, record_type: int, start: int, length: int) -> object:
    payload = message[start : start + length]
    if len(payload) != length:
        raise DnsDecodingError("truncated rdata")
    if record_type == TYPE_A:
        if length != 4:
            raise DnsDecodingError("invalid A record length", length=length)
        return str(ipaddress.IPv4Address(payload))
    if record_type == TYPE_AAAA:
        if length != 16:
            raise DnsDecodingError("invalid AAAA record length", length=length)
        return str(ipaddress.IPv6Address(payload))
    if record_type in NAME_TYPES:
        name, _ = decode_name(message, start)
        return name
    if record_type == TYPE_MX:
        preference = struct.unpack("!H", payload[:2])[0]
        exchange, _ = decode_name(message, start + 2)
        return {"preference": preference, "exchange": exchange}
    if record_type == TYPE_TXT:
        return _decode_character_strings(message, start, start + length)
    if record_type == TYPE_SOA:
        primary, position = decode_name(message, start)
        responsible, position = decode_name(message, position)
        serial, refresh, retry, expire, minimum = struct.unpack("!IIIII", message[position : position + 20])
        return {
            "primary": primary,
            "responsible": responsible,
            "serial": serial,
            "refresh": refresh,
            "retry": retry,
            "expire": expire,
            "minimum": minimum,
        }
    if record_type == TYPE_SRV:
        priority, weight, port = struct.unpack("!HHH", payload[:6])
        target, _ = decode_name(message, start + 6)
        return {"priority": priority, "weight": weight, "port": port, "target": target}
    return payload.hex()


def parse_response(message: bytes) -> dict:
    if len(message) < HEADER_SIZE:
        raise DnsDecodingError("message shorter than header", length=len(message))
    transaction_id, flags, question_count, answer_count, authority_count, additional_count = struct.unpack(
        HEADER_FORMAT, message[:HEADER_SIZE]
    )
    question_name, position = decode_name(message, HEADER_SIZE)
    if position + 4 > len(message):
        raise DnsDecodingError("truncated question section")
    question_type, question_class = struct.unpack("!HH", message[position : position + 4])
    position += 4
    sections = {"answer": answer_count, "authority": authority_count, "additional": additional_count}
    records: list[dict] = []
    total_records = answer_count + authority_count + additional_count
    for _ in range(total_records):
        name, position = decode_name(message, position)
        if position + 10 > len(message):
            raise DnsDecodingError("truncated record header")
        record_type, record_class, ttl, data_length = struct.unpack("!HHIH", message[position : position + 10])
        position += 10
        if position + data_length > len(message):
            raise DnsDecodingError("truncated record data")
        value = _decode_rdata(message, record_type, position, data_length)
        position += data_length
        records.append(
            {
                "name": name,
                "type": TYPE_NAMES.get(record_type, str(record_type)),
                "type_code": record_type,
                "class": record_class,
                "ttl": ttl,
                "value": value,
            }
        )
    return {
        "transaction_id": transaction_id,
        "truncated": bool(flags & 0x0200),
        "recursion_desired": bool(flags & 0x0100),
        "recursion_available": bool(flags & 0x0080),
        "rcode": flags & 0x000F,
        "rcode_name": RCODE_NAMES.get(flags & 0x000F, "UNKNOWN"),
        "question": {"name": question_name, "type": TYPE_NAMES.get(question_type, str(question_type)), "class": question_class},
        "record_counts": {"answer": answer_count, "authority": authority_count, "additional": additional_count},
        "sections": sections,
        "records": records,
        "message_length": len(message),
    }


def min_ttl(parsed: dict, default: int = 60) -> int:
    values = [record["ttl"] for record in parsed.get("records", []) if record["ttl"] > 0]
    return min(values) if values else default
