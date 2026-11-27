# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""The shared server kit answers every failure with JSON, and trusts a proxy's address only when told to."""

import json
import threading
import urllib.request
from pathlib import Path

from mo_rong import App, HttpError, Settings
from mo_rong.vn import month_of


def kit(**settings):
    app = App("thu", Path(__file__).parent, Settings(token="", secret="k", **settings))
    seen = {}

    @app.route("GET", "/loi")
    def broken(request):
        raise RuntimeError("bug")

    @app.route("POST", "/so")
    def number(request):
        return {"n": int(request.json()["n"])}

    @app.route("GET", "/thang")
    def month(request):
        return {"m": month_of(request.query.get("t"))}

    @app.route("GET", "/ip")
    def address(request):
        seen["ip"] = request.client_ip
        return {"ip": request.client_ip}

    @app.route("GET", "/het")
    def gone(request):
        raise HttpError(410, "Hết.")

    return app, seen


def test_failures_are_answered_in_json_without_leaking_details():
    app, _ = kit()
    crash = app.handle("GET", "/loi")
    assert crash.status == 500 and crash.data["error"] == "server_error" and "bug" not in crash.body.decode()
    bad = app.handle("POST", "/so", {}, json.dumps({"n": "mười"}).encode())
    assert bad.status == 422 and bad.data["error"] == "invalid"
    missing = app.handle("POST", "/so", {}, b"{}")
    assert missing.status == 422
    month = app.handle("GET", "/thang?t=tháng mười")
    assert month.status == 422 and "2026-11" in month.data["message"]
    assert app.handle("GET", "/thang?t=11/2026").data == {"m": "2026-11"}
    assert app.handle("GET", "/het").status == 410
    assert app.handle("GET", "/khong-co").status == 404
    assert app.handle("GET", "/health").data["ok"] is True


def serve_once(app, header):
    server = app.server(0, "127.0.0.1")
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/ip", headers=header)
    with urllib.request.urlopen(request, timeout=5) as response:
        body = json.loads(response.read())
    thread.join(5)
    server.server_close()
    return body["ip"]


def test_a_forged_forwarded_header_is_ignored_unless_behind_a_trusted_proxy():
    forged = {"X-Forwarded-For": "1.2.3.4"}
    assert serve_once(kit()[0], forged) == "127.0.0.1"
    assert serve_once(kit(trust_proxy="1")[0], {"X-Forwarded-For": "9.9.9.9, 5.6.7.8"}) == "5.6.7.8"


def test_pages_get_the_shared_kit_and_desktinys_fonts_but_nothing_else_from_sdk():
    app, _ = kit()
    font = app.static("/ui/phong-chu/be-vietnam-pro-vietnamese-700-normal.woff2")
    assert font.status == 200 and font.content_type == "font/woff2"
    assert font.body[:4] == b"wOF2"
    assert app.static("/ui/giao-dien.css").status == 200
    assert app.static("/ui/bieu-do.js").status == 200
    # Only fonts by bare name: no licence texts, no other folders, no climbing out.
    for path in ("/ui/phong-chu/OFL-BeVietnamPro.txt", "/ui/phong-chu/../mo-rong.js", "/ui/phong-chu/x/a.woff2",
                 "/ui/phong-chu/khong-co.woff2"):
        assert app.static(path) is None, path


def test_a_negative_or_oversized_content_length_is_refused_before_reading():
    import http.client
    import socket

    from mo_rong import server as kit_server

    app, _ = kit()
    server = app.server(0, "127.0.0.1")
    assert server.RequestHandlerClass.timeout == 30  # a stalled client cannot hold a thread forever
    for length in ("-1", "abc", str(kit_server.MAX_BODY + 1)):
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.putrequest("POST", "/so")
        conn.putheader("Content-Length", length)
        conn.endheaders()
        try:
            assert conn.getresponse().status == 413
        except (ConnectionError, socket.timeout):  # pragma: no cover
            raise AssertionError(f"Content-Length {length} was not refused") from None
        conn.close()
        thread.join(5)
    server.server_close()
