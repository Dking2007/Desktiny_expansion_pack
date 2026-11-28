# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""A small web server for connected Desktiny plugins: routes, signed calls, frame viewers, static pages.

Standard library plus the `desktiny-plugin` SDK. Each plugin builds an `App`, adds routes and runs it:

    app = App("cham-cong", Path(__file__).parent)
    @app.route("GET", "/api/toi", viewer=True)
    def mine(request): return {"user": request.viewer["user"]}
    app.run(9201)

* `signed=True` routes accept only what Desktiny signed with the plugin's secret (events, steps, tools).
* `viewer=True` routes need the frame's session token in `X-Desktiny-Session`; the app asks Desktiny who it
  belongs to (`GET /plugin/v1/me`) and passes it on as `request.viewer`. `admin=True` also needs the token to
  come from the plugin's `admin.page` frame, which Desktiny gives only to organisation managers.
* Files under `ui/` and the frame SDK are served as they are.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from desktiny_plugin import Client, PluginError, SignatureError, verify

from .vn import InputError

SDK = Path(__file__).resolve().parents[2] / "sdk" / "desktiny-plugin-sdk.js"
MAX_BODY = 2_000_000
# The frame SDK, the shared page helper and styles, served to every plugin's pages from sdk/.
SHARED = {"desktiny-plugin-sdk.js", "mo-rong.js", "chung.css", "giao-dien.css", "bieu-do.js"}
FONTS = SDK.parent / "phong-chu"
MAX_VIEWERS = 2000
logger = logging.getLogger("mo_rong")
STATIC_TYPES = {".html", ".js", ".css", ".svg", ".png", ".json", ".ico", ".webp"}


class HttpError(Exception):
    def __init__(self, status: int, message: str, code: str = "error"):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: bytes = b""
    params: dict[str, str] = field(default_factory=dict)
    viewer: dict | None = None
    client_ip: str = ""

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)

    def json(self) -> dict:
        try:
            data = json.loads(self.body or b"{}")
        except ValueError as exc:
            raise HttpError(400, "Nội dung không phải JSON.") from exc
        if not isinstance(data, dict):
            raise HttpError(400, "Nội dung phải là một đối tượng JSON.")
        return data

    @property
    def session_token(self) -> str:
        return self.header("x-desktiny-session")


@dataclass
class Response:
    status: int = 200
    body: bytes = b""
    content_type: str = "application/json"
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def data(self):
        return json.loads(self.body) if self.content_type.startswith("application/json") and self.body else None


def json_response(data, status: int = 200) -> Response:
    return Response(status, json.dumps(data, ensure_ascii=False, default=str).encode())


@dataclass
class Route:
    method: str
    pattern: re.Pattern
    handler: Callable
    signed: bool = False
    viewer: bool = False
    admin: bool = False


class Settings:
    """Where the plugin finds Desktiny and its keys; read from the environment, overridable in tests."""

    def __init__(self, **values):
        env = os.environ
        self.desktiny_url = values.get("desktiny_url", env.get("DESKTINY_URL", "http://localhost:8080"))
        self.token = values.get("token", env.get("DESKTINY_TOKEN", ""))
        self.secret = values.get("secret", env.get("DESKTINY_SECRET", ""))
        self.data_dir = Path(values.get("data_dir", env.get("DATA_DIR", "data")))
        # Only behind a reverse proxy that sets it: otherwise anyone could pick their own address.
        self.trust_proxy = str(values.get("trust_proxy", env.get("TRUST_PROXY", ""))).lower() in {"1", "true", "yes"}


class App:
    def __init__(self, name: str, root: Path, settings: Settings | None = None):
        self.name, self.root = name, root
        self.settings = settings or Settings()
        self.routes: list[Route] = []
        self._viewers: dict[str, tuple[float, dict]] = {}
        self._org_settings: tuple[float, dict] | None = None
        # Tests replace how the app reaches Desktiny: a function (token) -> object with Client's methods.
        self.client_factory: Callable[[str], Client] = lambda token: Client(
            self.settings.desktiny_url, token, secret=self.settings.secret
        )
        self.route("GET", "/health")(lambda request: {"ok": True, "plugin": self.name})

    # ---- Routes -------------------------------------------------------------------------------

    def route(self, method: str, path: str, *, signed=False, viewer=False, admin=False):
        pattern = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$")

        def register(handler):
            self.routes.append(Route(method, pattern, handler, signed, viewer or admin, admin))
            return handler

        return register

    # ---- Desktiny -----------------------------------------------------------------------------

    @property
    def desktiny(self) -> Client:
        """The plugin API with the installation token."""
        return self.client_factory(self.settings.token)

    def as_viewer(self, request: Request) -> Client:
        """The plugin API with the frame's session token: reads and writes as the person looking at it."""
        return self.client_factory(request.session_token)

    def org_settings(self, defaults: dict | None = None) -> dict:
        """The organisation's settings for the plugin (Quản trị › Plugin › Cấu hình), cached a minute."""
        now = time.monotonic()
        if not self._org_settings or now - self._org_settings[0] > 60:
            try:
                values = self.desktiny.settings() if self.settings.token else {}
            except (PluginError, OSError):
                values = self._org_settings[1] if self._org_settings else {}
            self._org_settings = (now, values)
        return {**(defaults or {}), **{k: v for k, v in self._org_settings[1].items() if v not in (None, "")}}

    def forget_settings(self):
        self._org_settings = None

    def who(self, request: Request) -> dict:
        token = request.session_token
        if not token:
            raise HttpError(401, "Trang cần mở trong Desktiny (thiếu phiên).", "session_missing")
        cached = self._viewers.get(token)
        if cached and time.monotonic() - cached[0] < 60:
            return cached[1]
        try:
            me = self.client_factory(token).me()
        except PluginError as exc:
            raise HttpError(401, "Phiên Desktiny không hợp lệ hoặc đã hết hạn.", "session_invalid") from exc
        if not me.get("user"):
            raise HttpError(401, "Phiên này không gắn với người dùng.", "session_invalid")
        if len(self._viewers) >= MAX_VIEWERS:  # sessions last minutes; drop the stale ones
            now = time.monotonic()
            self._viewers = {k: v for k, v in self._viewers.items() if now - v[0] < 60}
        self._viewers[token] = (time.monotonic(), me)
        return me

    # ---- Handling -------------------------------------------------------------------------------

    def handle(self, method: str, target: str, headers: dict | None = None, body: bytes = b"", client_ip: str = "") -> Response:
        parts = urlsplit(target)
        request = Request(method, parts.path, {k: v[0] for k, v in parse_qs(parts.query).items()},
                          {k.lower(): v for k, v in (headers or {}).items()}, body, client_ip=client_ip)  # fmt: skip
        try:
            if method == "OPTIONS":
                return Response(204)
            if method == "GET" and (static := self.static(parts.path)):
                return static
            for route in self.routes:
                found = route.pattern.match(parts.path)
                if not found or route.method != method:
                    continue
                request.params = found.groupdict()
                if route.signed:
                    try:
                        verify(self.settings.secret, request.header("x-desktiny-timestamp"), body,
                               request.header("x-desktiny-signature"))  # fmt: skip
                    except SignatureError as exc:
                        raise HttpError(401, "Chữ ký không hợp lệ.", "signature_invalid") from exc
                if route.viewer:
                    request.viewer = self.who(request)
                    if route.admin and (request.viewer.get("context") or {}).get("slot") != "admin.page":
                        raise HttpError(403, "Chỉ dùng được từ trang quản trị của plugin.", "admin_only")
                result = route.handler(request)
                return result if isinstance(result, Response) else json_response(result)
            raise HttpError(404, "Không tìm thấy.", "not_found")
        except HttpError as exc:
            return json_response({"error": exc.code, "message": exc.message}, exc.status)
        except PluginError as exc:
            return json_response({"error": exc.code, "message": exc.detail}, 502 if exc.status >= 500 else exc.status)
        except InputError as exc:
            return json_response({"error": "invalid", "message": str(exc)}, 422)
        except (ValueError, KeyError, TypeError) as exc:
            # A field missing or of the wrong kind in what the page sent.
            logger.info("[%s] %s %s: dữ liệu không hợp lệ (%r)", self.name, method, parts.path, exc)
            return json_response({"error": "invalid", "message": "Dữ liệu gửi lên không hợp lệ."}, 422)
        except Exception:
            logger.exception("[%s] %s %s lỗi", self.name, method, parts.path)
            return json_response({"error": "server_error", "message": "Máy chủ plugin gặp lỗi; đã ghi nhật ký."}, 500)

    def static(self, path: str) -> Response | None:
        # The fonts every page shares (Desktiny's own faces), served from sdk/phong-chu by bare file name.
        if path.startswith("/ui/phong-chu/"):
            name = path.rsplit("/", 1)[-1]
            font = FONTS / name
            if name.endswith(".woff2") and "/" not in path[len("/ui/phong-chu/"):] and font.is_file():
                return Response(200, font.read_bytes(), "font/woff2")
            return None
        shared = SDK.parent / path.rsplit("/", 1)[-1]
        if path.startswith("/ui/") and shared.name in SHARED and shared.is_file():
            kind = "text/css" if shared.suffix == ".css" else "text/javascript"
            return Response(200, shared.read_bytes(), kind + "; charset=utf-8")
        if not path.startswith(("/ui/", "/cong/")) or ".." in path:
            return None
        target = (self.root / path.lstrip("/")).resolve()
        if target.suffix not in STATIC_TYPES or not target.is_file() or self.root.resolve() not in target.parents:
            return None
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind in {"application/javascript", "image/svg+xml"}:
            kind += "; charset=utf-8"
        return Response(200, target.read_bytes(), kind)

    # ---- Serving --------------------------------------------------------------------------------

    def server(self, port: int, host: str = "0.0.0.0") -> ThreadingHTTPServer:
        app = self

        class Handler(BaseHTTPRequestHandler):
            timeout = 30  # a stalled client must not hold a thread for ever

            def log_message(self, *args):
                pass

            def _any(self):
                try:
                    size = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    size = -1
                if not 0 <= size <= MAX_BODY:
                    self.send_error(413)
                    return
                body = self.rfile.read(size) if size else b""
                address = self.client_address[0]
                if app.settings.trust_proxy:
                    # The proxy appends the address it saw: the last entry is the one it vouches for.
                    address = self.headers.get("X-Forwarded-For", "").split(",")[-1].strip() or address
                result = app.handle(self.command, self.path, dict(self.headers), body, address)
                self.send_response(result.status)
                self.send_header("Content-Type", result.content_type)
                # Frames are sandboxed (origin "null"); they call with a session token, never cookies.
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Desktiny-Session")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                for key, value in result.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(result.body)

            do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = _any

        return ThreadingHTTPServer((host, port), Handler)

    def every(self, seconds: Callable[[], float], job: Callable[[], None]):
        """Run `job` in the background every `seconds()` (read again each time, so settings apply live)."""

        def loop():
            while True:
                time.sleep(max(30.0, float(seconds())))
                try:
                    job()
                except Exception as exc:  # noqa: BLE001 (a failed round must not stop the next ones)
                    print(f"[{self.name}] lỗi khi chạy định kỳ: {exc}", flush=True)

        threading.Thread(target=loop, daemon=True).start()

    def run(self, port: int):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        port = int(os.environ.get("PORT", port))
        sys.stdout.reconfigure(encoding="utf-8")  # a Windows console's code page has no Vietnamese
        print(f"[{self.name}] đang chạy ở cổng {port}", flush=True)
        self.server(port).serve_forever()
