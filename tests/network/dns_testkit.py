"""Local DNS test servers used by transport and resolver tests."""

from __future__ import annotations

import http.server
import socket
import ssl
import struct
import subprocess
import threading
from pathlib import Path

from dns.wire import TYPE_A, TYPE_AAAA, encode_name

ANSWER_ADDRESS_V4 = "203.0.113.7"
ANSWER_ADDRESS_V6 = "2001:db8::7"
TC_BIT = 0x0200


def build_response(query: bytes, truncated: bool = False, rcode: int = 0, address: str = ANSWER_ADDRESS_V4, ttl: int = 30) -> bytes:
    transaction_id, flags, question_count = struct.unpack("!HHH", query[:6])
    question_name, position = decode_question(query)
    question_type, question_class = struct.unpack("!HH", query[position : position + 4])
    response_flags = 0x8180 | rcode
    if truncated:
        response_flags |= TC_BIT
        answers = b""
        answer_count = 0
    else:
        payload = socket.inet_aton(address) if question_type == TYPE_A else socket.inet_pton(socket.AF_INET6, address)
        answers = encode_name(question_name) + struct.pack("!HHIH", question_type, 1, ttl, len(payload)) + payload
        answer_count = 1
    header = struct.pack("!HHHHHH", transaction_id, response_flags, question_count, answer_count, 0, 0)
    question = encode_name(question_name) + struct.pack("!HH", question_type, question_class)
    return header + question + answers


def decode_question(query: bytes) -> tuple[str, int]:
    position = 12
    labels: list[str] = []
    while True:
        length = query[position]
        if length == 0:
            position += 1
            break
        position += 1
        labels.append(query[position : position + length].decode("ascii"))
        position += length
    return ".".join(labels), position


def read_question_name(message: bytes) -> str:
    name, _ = decode_question(message)
    return name


class UdpDnsServer:
    """UDP DNS server with optional truncation for selected names."""

    def __init__(
        self,
        truncated_names: set[str] | None = None,
        silent: bool = False,
        address: str = ANSWER_ADDRESS_V4,
        port: int | None = None,
    ) -> None:
        self.truncated_names = truncated_names or set()
        self.silent = silent
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", port or 0))
        self.port = self.socket.getsockname()[1]
        self.queries: list[str] = []
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.running = True

    def start(self) -> "UdpDnsServer":
        self.thread.start()
        return self

    def _serve(self) -> None:
        while self.running:
            try:
                payload, client = self.socket.recvfrom(4096)
            except OSError:
                return
            name = read_question_name(payload)
            self.queries.append(name)
            if self.silent:
                continue
            truncated = name in self.truncated_names
            response = build_response(payload, truncated=truncated, address=self.address)
            try:
                self.socket.sendto(response, client)
            except OSError:
                return

    def stop(self) -> None:
        self.running = False
        try:
            self.socket.close()
        except OSError:
            pass


class TcpDnsServer:
    """TCP DNS server with length prefixed messages."""

    def __init__(self, address: str = ANSWER_ADDRESS_V4) -> None:
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(8)
        self.port = self.socket.getsockname()[1]
        self.running = True
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> "TcpDnsServer":
        self.thread.start()
        return self

    def _serve(self) -> None:
        while self.running:
            try:
                connection, _ = self.socket.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(connection,), daemon=True).start()

    def _handle(self, connection: socket.socket) -> None:
        with connection:
            try:
                prefix = connection.recv(2)
                if len(prefix) < 2:
                    return
                length = int.from_bytes(prefix, "big")
                query = b""
                while len(query) < length:
                    chunk = connection.recv(length - len(query))
                    if not chunk:
                        return
                    query += chunk
                response = build_response(query, address=self.address)
                connection.sendall(len(response).to_bytes(2, "big") + response)
            except OSError:
                return

    def stop(self) -> None:
        self.running = False
        try:
            self.socket.close()
        except OSError:
            pass


class TlsDnsServer(TcpDnsServer):
    """TCP DNS server wrapped in TLS for DNS over TLS tests."""

    def __init__(self, cert_path: Path, key_path: Path, address: str = ANSWER_ADDRESS_V4) -> None:
        super().__init__(address=address)
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    def _handle(self, connection: socket.socket) -> None:
        try:
            with self.context.wrap_socket(connection, server_side=True) as wrapped:
                prefix = wrapped.recv(2)
                if len(prefix) < 2:
                    return
                length = int.from_bytes(prefix, "big")
                query = b""
                while len(query) < length:
                    chunk = wrapped.recv(length - len(query))
                    if not chunk:
                        return
                    query += chunk
                response = build_response(query, address=self.address)
                wrapped.sendall(len(response).to_bytes(2, "big") + response)
        except (ssl.SSLError, OSError):
            return


class DohRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that answers RFC 8484 POST requests."""

    server_version = "DohTestServer/1.0"
    address = ANSWER_ADDRESS_V4
    content_type = "application/dns-message"
    status_code = 200

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        query = self.rfile.read(length)
        if self.path != "/dns-query":
            self.send_error(404)
            return
        response = build_response(query, address=self.address)
        self.send_response(self.status_code)
        self.send_header("Content-Type", self.content_type)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, *args) -> None:
        return None


class DohServer:
    """HTTPS server implementing DNS over HTTPS for tests."""

    def __init__(self, cert_path: Path, key_path: Path, content_type: str = "application/dns-message", status_code: int = 200) -> None:
        handler = type("BoundDohHandler", (DohRequestHandler,), {"content_type": content_type, "status_code": status_code})
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
        self.httpd.socket = context.wrap_socket(self.httpd.socket, server_side=True)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> "DohServer":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def generate_certificate(directory: Path) -> tuple[Path, Path]:
    """Create a self signed certificate valid for localhost and loopback addresses."""

    directory.mkdir(parents=True, exist_ok=True)
    cert_path = directory / "server.crt"
    key_path = directory / "server.key"
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path
    command = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-days",
        "2",
        "-subj",
        "/CN=localhost",
        "-addext",
        "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]
    subprocess.run(command, check=True, capture_output=True)
    return cert_path, key_path


def trusted_context(cert_path: Path) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=str(cert_path))
    return context


def unused_port() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port
