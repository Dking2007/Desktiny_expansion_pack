# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""A pretend Desktiny for the plugin tests: answers the plugin API from memory and records what it was asked."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

from desktiny_plugin import PluginError, sign

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from mo_rong import Settings, Store  # noqa: E402

SECRET = "khoa-ky-thu"


def load(plugin: str):
    """The plugin's server module (expansion/<bản mở rộng>/plugins/<name>/server.py)."""
    (path,) = ROOT.glob(f"expansion/*/plugins/{plugin}/server.py")
    spec = importlib.util.spec_from_file_location(f"plugin_{plugin.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeDesktiny:
    def __init__(self):
        self.users = {"u-an": {"id": "u-an", "display_name": "Nguyễn Văn An"},
                      "u-binh": {"id": "u-binh", "display_name": "Trần Thị Bình"},
                      "u-admin": {"id": "u-admin", "display_name": "Lê Quản Trị"}}  # fmt: skip
        # session token -> (user id, slot)
        self.sessions = {"phien-an": ("u-an", "page"), "phien-binh": ("u-binh", "page"),
                         "phien-qt": ("u-admin", "admin.page")}  # fmt: skip
        self.settings: dict = {}
        self.cases: dict[str, dict] = {}
        self.files: dict[str, tuple[str, str, bytes]] = {}  # file id -> (case id, name, bytes)
        self.calls: list[tuple] = []

    def client(self, token: str):
        return FakeClient(self, token)


class FakeClient:
    def __init__(self, desktiny: FakeDesktiny, token: str):
        self.d, self.token = desktiny, token

    def _record(self, name, *args, **kwargs):
        self.d.calls.append((name, self.token, args, kwargs))

    def me(self):
        if self.token in self.d.sessions:
            user_id, slot = self.d.sessions[self.token]
            return {"user": self.d.users[user_id], "kind": "session", "context": {"slot": slot}, "api_version": 2}
        if self.token == "cai-dat":
            return {"user": None, "kind": "install", "context": {}, "api_version": 2}
        raise PluginError(401, "plugin_token_invalid", "x")

    def settings(self):
        return dict(self.d.settings)

    def send_event(self, event_type, data=None, key=None):
        self._record("send_event", event_type, data, key=key)
        return {"accepted": True}

    def people(self, department_id=None, cursor=None, limit=100):
        return {"items": list(self.d.users.values()), "next_cursor": None}

    def departments(self):
        return {"items": [{"id": "d1", "name": "Phòng Hành chính"}]}

    def case(self, case_id):
        if case_id not in self.d.cases:
            raise PluginError(404, "case_not_found", "x")
        return self.d.cases[case_id]

    def cases(self, form_id=None, status=None, updated_since=None, cursor=None, limit=100):
        items = [c for c in self.d.cases.values() if not form_id or c["form"]["id"] == form_id]
        return {"items": items, "next_cursor": None, "has_more": False}

    def case_files(self, case_id):
        return [{"id": fid, "name": name, "type": "application/pdf"} for fid, (cid, name, _) in self.d.files.items() if cid == case_id]

    def file_content(self, case_id, file_id):
        return self.d.files[file_id][2]

    def attach(self, case_id, name, content, mime="application/octet-stream", *, node_id=None, role="attachment", key=None):
        self._record("attach", case_id, name, content, mime=mime, node_id=node_id, role=role, key=key)
        return {"id": f"tep-{len(self.d.calls)}", "name": name}

    def notify(self, title, user_ids=None, **kwargs):
        self._record("notify", title, user_ids, **kwargs)
        return {"sent": len(user_ids or [])}

    def comment_case(self, case_id, body, key=None):
        self._record("comment_case", case_id, body, key=key)
        return {"id": "y-kien"}

    def write_fields(self, case_id, values, key=None):
        self._record("write_fields", case_id, values, key=key)
        self.d.cases.setdefault(case_id, {"payload": {}})["payload"].update(values)
        return {"case_id": case_id}

    def complete_call(self, call_id, branch="success", output=None, message=""):
        self._record("complete_call", call_id, branch, output, message)
        return {"accepted": True}

    def call_progress(self, call_id, message):
        self._record("call_progress", call_id, message)
        return {}


@pytest.fixture
def desktiny():
    return FakeDesktiny()


@pytest.fixture
def make_app(desktiny, tmp_path):
    def make(plugin: str, **kwargs):
        module = load(plugin)
        settings = Settings(token="cai-dat", secret=SECRET, desktiny_url="http://desktiny.test", data_dir=tmp_path)
        app = module.build(settings, **kwargs)
        app.client_factory = desktiny.client
        return app

    return make


def call(app, method, path, body=None, session=None, raw=None):
    headers = {"Content-Type": "application/json"}
    if session:
        headers["X-Desktiny-Session"] = session
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
    return app.handle(method, path, headers, data)


def signed(app, path, body: dict):
    raw = json.dumps(body, ensure_ascii=False).encode()
    stamp = str(int(time.time()))
    headers = {"X-Desktiny-Timestamp": stamp, "X-Desktiny-Signature": sign(SECRET, stamp, raw)}
    return app.handle("POST", path, headers, raw)


__all__ = ["FakeDesktiny", "Store", "call", "signed"]
