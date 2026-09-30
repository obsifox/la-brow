"""Application server hosting the environment platform interface and the web client."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.routes import Api, ApiError, MAX_REQUEST_BYTES
from profiles.errors import ProfileError

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
STATIC_ROOTS = {
    "/": "ui",
    "/assets": "assets",
    "/ui": "ui",
}
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
PROFILE_ROUTE = re.compile(r"^/api/profiles/(?P<profile>[A-Za-z0-9-]{1,64})(?:/(?P<action>export|rollback))?$")
EXTENSION_ROUTE = re.compile(r"^/api/extensions/(?P<extension>[a-z0-9][a-z0-9-]{0,62})$")

MIME_OVERRIDES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".md": "text/markdown; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
}


class RequestLog:
    """Collects structured request records without sensitive payloads."""

    def __init__(self, capacity: int = 200) -> None:
        self.capacity = capacity
        self.records: list[dict] = []
        self.lock = threading.Lock()

    def append(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self.lock:
            self.records.append({"method": method, "path": path, "status": status, "duration_ms": round(duration_ms, 2)})
            if len(self.records) > self.capacity:
                self.records = self.records[-self.capacity :]

    def recent(self, limit: int = 50) -> list[dict]:
        with self.lock:
            return list(reversed(self.records[-limit:]))


class ApplicationHandler(BaseHTTPRequestHandler):
    server_version = "LaBrowApplication/0.1.0"
    protocol_version = "HTTP/1.1"
    api: Api = None
    request_log: RequestLog = None
    repo_root: Path = REPO_ROOT

    def log_message(self, format_string: str, *arguments) -> None:
        return None

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _dispatch(self, method: str) -> None:
        import time

        started = time.perf_counter()
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        query = parse_qs(parts.query)
        status = 500
        try:
            if path.startswith("/api/"):
                status = self._handle_api(method, path, query)
            else:
                status = self._handle_static(method, path)
        except ApiError as error:
            status = error.status
            self._send_json(status, error.as_dict())
        except ProfileError as error:
            status = 400
            self._send_json(status, {"error": error.as_dict()})
        except BrokenPipeError:
            return
        except Exception as error:
            status = 500
            self._send_json(status, {"error": {"code": "internal_error", "message": str(error)}})
        finally:
            self.request_log.append(method, path, status, (time.perf_counter() - started) * 1000.0)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        if length > MAX_REQUEST_BYTES:
            raise ApiError(413, "payload_too_large", "request body exceeds the accepted size")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError(400, "invalid_json", "request body is not valid json", str(error)) from error
        if not isinstance(payload, dict):
            raise ApiError(400, "invalid_json", "request body must be a json object")
        return payload

    def _handle_api(self, method: str, path: str, query: dict) -> int:
        api = self.api
        if path == "/api/health" and method == "GET":
            return self._send_json(200, api.health(query))
        if path == "/api/settings" and method == "GET":
            return self._send_json(200, api.settings_get(query))
        if path == "/api/settings" and method == "PUT":
            return self._send_json(200, api.settings_put(query, self._read_body()))
        if path == "/api/environment" and method == "GET":
            return self._send_json(200, api.environment(query))
        if path == "/api/consistency" and method == "GET":
            return self._send_json(200, api.consistency(query))
        if path == "/api/diagnostics" and method == "GET":
            return self._send_json(200, api.diagnostics(query))
        if path == "/api/events" and method == "GET":
            return self._send_json(200, api.events(query))
        if path == "/api/identity" and method == "GET":
            return self._send_json(200, api.identity(query))
        if path == "/api/scans" and method == "GET":
            return self._send_json(200, api.scans(query))
        if path == "/api/webrtc" and method == "GET":
            return self._send_json(200, api.webrtc(query))
        if path == "/api/requests" and method == "GET":
            return self._send_json(200, {"requests": self.request_log.recent(30)})
        if path == "/api/resolvers" and method == "GET":
            return self._send_json(200, api.resolvers(query))
        if path == "/api/dns/probe" and method == "POST":
            return self._send_json(200, api.dns_probe(query, self._read_body()))
        if path == "/api/dns/diagnostics" and method == "GET":
            return self._send_json(200, api.dns_diagnostics(query))
        if path == "/api/extensions" and method == "GET":
            return self._send_json(200, api.extensions_list(query))
        if path == "/api/extensions/inspect" and method == "POST":
            return self._send_json(200, api.extensions_inspect(query, self._read_body()))
        if path == "/api/extensions/install" and method == "POST":
            return self._send_json(201, api.extensions_install(query, self._read_body()))
        if path == "/api/themes" and method == "GET":
            return self._send_json(200, api.themes(query))
        if path == "/api/themes/active" and method == "PUT":
            return self._send_json(200, api.themes_activate(query, self._read_body()))
        if path == "/api/compat/firefox-desktop" and method == "GET":
            return self._send_json(200, api.compat_matrix(query))
        extension_match = EXTENSION_ROUTE.match(path)
        if extension_match and method == "DELETE":
            return self._send_json(200, api.extensions_remove(extension_match.group("extension"), query))
        if path == "/api/profiles" and method == "GET":
            return self._send_json(200, api.profiles_list(query))
        if path == "/api/profiles" and method == "POST":
            body = self._read_body()
            profile_id = body.get("id") or body.get("profile_id") or (body.get("profile", {}).get("name") if isinstance(body.get("profile"), dict) else None)
            if not profile_id:
                raise ApiError(400, "invalid_body", "profile creation requires an id or a profile name")
            return self._send_json(201, api.profile_put(str(profile_id), query, body))
        if path == "/api/profiles/validate" and method == "POST":
            return self._send_json(200, api.profile_validate(query, self._read_body()))
        if path == "/api/profiles/import" and method == "POST":
            return self._send_json(200, api.profile_import(query, self._read_body()))
        match = PROFILE_ROUTE.match(path)
        if match:
            profile_id = match.group("profile")
            action = match.group("action")
            if action is None and method == "GET":
                return self._send_json(200, api.profile_get(profile_id, query))
            if action is None and method == "PUT":
                return self._send_json(200, api.profile_put(profile_id, query, self._read_body()))
            if action is None and method == "DELETE":
                return self._send_json(200, api.profile_delete(profile_id, query))
            if action == "export" and method == "GET":
                return self._send_json(200, api.profile_export(profile_id, query))
            if action == "rollback" and method == "POST":
                return self._send_json(200, api.profile_rollback(profile_id, query))
        raise ApiError(404, "not_found", "no route matches the requested path", {"path": path, "method": method})

    def _resolve_static(self, path: str) -> Path | None:
        if not path.startswith("/"):
            return None
        if path == "/":
            return self.repo_root / "ui" / "index.html"
        segments = [segment for segment in path.split("/") if segment]
        if not segments:
            return None
        for segment in segments:
            if not SAFE_SEGMENT.match(segment) or segment in {".", ".."}:
                return None
        root_key = "/" + segments[0]
        if root_key in STATIC_ROOTS:
            relative = Path(*segments[1:]) if segments[0] in {"ui", "assets"} else Path(*segments)
            candidate = (self.repo_root / STATIC_ROOTS[root_key] / relative).resolve()
        else:
            candidate = (self.repo_root / STATIC_ROOTS["/"] / Path(*segments)).resolve()
        try:
            candidate.relative_to(self.repo_root.resolve())
        except ValueError:
            return None
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if candidate.is_file():
            return candidate
        return None

    def _handle_static(self, method: str, path: str) -> int:
        if method != "GET":
            raise ApiError(405, "method_not_allowed", "static resources are served over GET only")
        target = self._resolve_static(path)
        if target is None:
            raise ApiError(404, "not_found", "static resource not found", {"path": path})
        content_type = MIME_OVERRIDES.get(target.suffix.lower())
        if content_type is None:
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        payload = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(payload)
        return 200

    def _send_json(self, status: int, payload: dict) -> int:
        body = json.dumps(payload, ensure_ascii=True, sort_keys=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)
        return status


def build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, repo: Path | None = None) -> ThreadingHTTPServer:
    repo_root = Path(repo).resolve() if repo else REPO_ROOT
    handler = type(
        "BoundApplicationHandler",
        (ApplicationHandler,),
        {"api": Api(repo_root), "request_log": RequestLog(), "repo_root": repo_root},
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the LA Brow application server")
    parser.add_argument("--host", default=os.environ.get("LABROW_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("LABROW_PORT", DEFAULT_PORT)))
    parser.add_argument("--repo", default=str(REPO_ROOT))
    arguments = parser.parse_args()
    server = build_server(arguments.host, arguments.port, Path(arguments.repo))
    address = server.server_address
    print(f"application server listening on {arguments.host}:{address[1]}")
    print(f"web client: http://localhost:{address[1]}/")
    print(f"interface:  http://localhost:{address[1]}/api/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("application server stopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
