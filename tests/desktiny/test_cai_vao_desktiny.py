# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Install everything into a real Desktiny (its own test fixture: Workspace + Core, in memory) and run flows that go
through the plugins' servers. Needs a Desktiny checkout: DESKTINY_DIR=/path/to/Desktiny (skipped otherwise).

    DESKTINY_DIR=/path/to/Desktiny python -m pytest tests/desktiny   (DESKTINY_DIR points at a Desktiny checkout)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

DESKTINY = Path(os.environ.get("DESKTINY_DIR", "")).resolve() if os.environ.get("DESKTINY_DIR") else None
if not DESKTINY or not (DESKTINY / "services/workspace-api/tests/test_workspace.py").is_file():
    pytest.skip("Đặt DESKTINY_DIR trỏ tới mã nguồn Desktiny để chạy thử cài đặt thật.", allow_module_level=True)

TESTS = DESKTINY / "services/workspace-api/tests"
sys.path[:0] = [str(TESTS), str(DESKTINY / "services/workspace-api/src")]
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import dong_goi  # noqa: E402
import httpx  # noqa: E402
from conftest import load  # noqa: E402  (the expansion pack's own test helpers)
from dx_workspace import automations as desktiny_automations  # noqa: E402
from dx_workspace import plugins as desktiny_plugins  # noqa: E402
from test_workspace import drain  # noqa: E402
from test_workspace import world as world  # noqa: E402,F401  (Desktiny's two-service fixture)

from desktiny_plugin import Client, PluginError  # noqa: E402
from mo_rong import Settings  # noqa: E402

API = "/workspace/v1"


def as_(env, name):
    env[6][0] = env[5][name]
    return env[0]


def upload(client, path, name, data: bytes, kind="application/zip", **form):
    return client.post(API + path, files={"file": (name, data, kind)}, data=form)


class InProcessClient(Client):
    """The SDK client, speaking to the test Desktiny instead of over the network."""

    def __init__(self, http, token, secret=""):
        super().__init__("http://desktiny.test", token, secret=secret)
        self.http = http

    def request(self, method, path, body=None, *, key=None, raw=False, files=None, signed=False):
        import time
        import uuid

        from desktiny_plugin import sign

        headers = {"Authorization": f"Bearer {self.token}"}
        if method != "GET":
            headers["Idempotency-Key"] = key or uuid.uuid4().hex
        content = None
        if files is None and body is not None:
            content = json.dumps(body, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        if signed:
            stamp = str(int(time.time()))
            headers |= {"X-Desktiny-Timestamp": stamp, "X-Desktiny-Signature": sign(self.secret, stamp, content or b"")}
        response = self.http.request(method, API + "/plugin/v1" + path, headers=headers, content=content,
                                     files={k: v for k, v in (files or {}).items()} or None,
                                     data=body if files is not None else None)  # fmt: skip
        if response.status_code >= 400:
            error = response.json() if response.content else {}
            raise PluginError(response.status_code, error.get("code", "http_error"), error.get("detail", ""))
        if raw:
            return response.content, dict(response.headers)
        return response.json() if response.content else {}


def connect(env, plugin: str, issued: dict, tmp_path):
    """The plugin's server, wired to the test Desktiny both ways."""
    app = load(plugin).build(Settings(token=issued["token"], secret=issued["secret"], data_dir=tmp_path / plugin))
    app.client_factory = lambda token: InProcessClient(env[0], token, issued["secret"])
    return app


def serve(apps: dict[str, object]):
    """Desktiny's calls to plugin servers (by port) answered by the plugins' apps in this process."""

    def answer(request: httpx.Request) -> httpx.Response:
        app = apps[request.url.port]
        result = app.handle(request.method, request.url.raw_path.decode(), dict(request.headers), request.content)
        return httpx.Response(result.status, content=result.body, headers={"Content-Type": result.content_type})

    desktiny_plugins.use_transport(httpx.MockTransport(answer))


def approve(director, plugin_id: str, revision: int, manifest: dict, **extra):
    body = {"expected_revision": revision, "permissions": manifest.get("permissions", []), "events": manifest.get("events", []),
            "fields": (manifest.get("writes") or {}).get("fields", []), "frame_permissions": manifest.get("frame_permissions", []),
            "assistant_tools": [t["name"] for t in manifest.get("assistant_tools", [])], **extra}  # fmt: skip
    approved = director.post(f"{API}/plugins/{plugin_id}/approve", json=body)
    assert approved.status_code == 200, approved.text
    return approved.json()


def test_every_pack_installs_publish_every_process_and_pass_the_contrast_check(world):  # noqa: F811
    director = as_(world, "director")
    for name, activate in (("nhan-su", "false"), ("van-thu", "false"), ("mot-cua-xa", "true")):
        files = dong_goi.pack_files(name)
        preview = upload(director, "/packs/preview", f"{name}.zip", dong_goi.zipped(files))
        assert preview.status_code == 200, preview.text
        installed = upload(director, "/packs", f"{name}.zip", dong_goi.zipped(files), activate=activate)
        assert installed.status_code == 201, installed.text
        manifest = json.loads(files["desktiny-pack.json"])
        names = {json.loads(files[path])["name"] for path in manifest["processes"]}
        available = {item["name"] for item in as_(world, "staff").get(API + "/processes/available").json()["items"]}
        assert names <= available, (names - available, installed.json())
        director = as_(world, "director")
        # The pack's flows are installed switched off, for the organisation to turn on.
        flows = {json.loads(files[path])["name"] for path in manifest.get("automations", [])}
        rules = {r["name"]: r for r in director.get(API + "/automations?limit=200").json()["items"]}
        assert flows and flows <= set(rules), flows - set(rules)
        assert not any(rules[name]["enabled"] for name in flows)
    look = director.get(API + "/appearance").json()
    assert look["pack_id"] == "vn.mo-rong.mot-cua-xa" and look["appearance"]["login"]["button_label"] == "Đăng nhập cán bộ"


def test_every_plugin_installs_and_its_pages_and_steps_are_offered(world, tmp_path):  # noqa: F811
    world[8].plugin_allowed_hosts = "localhost"
    director = as_(world, "director")
    packaged, connected = dong_goi.plugins()
    for name in packaged:
        installed = upload(director, "/plugins", f"{name}.zip", dong_goi.zipped(dong_goi.packaged_plugin_files(name)))
        assert installed.status_code == 201, (name, installed.text)
        approve(director, installed.json()["id"], installed.json()["revision"], json.loads(dong_goi.packaged_plugin_files(name)["desktiny-plugin.json"]))
    for name in connected:
        # The .zip the build hands out (manifest only); the flow tests below upload the bare manifest.
        manifest = dong_goi.manifest(name)
        installed = upload(director, "/plugins", f"{name}.zip", dong_goi.zipped(dong_goi.connected_plugin_files(name)))
        assert installed.status_code == 201, (name, installed.text)
        approve(director, manifest["id"], installed.json()["revision"], manifest)
    rows = {row["id"]: row for row in director.get(API + "/plugins").json()["items"]}
    assert len(rows) == len(packaged) + len(connected) and {r["state"] for r in rows.values()} == {"enabled"}
    nodes = {n["kind"] for n in director.get(API + "/plugins/nodes").json()["items"]}
    assert {"cap_so_van_ban", "ky_so_van_ban", "chot_ky_luong", "vao_so_van_ban_den"} <= nodes
    staff = as_(world, "staff")
    pages = staff.get(API + "/plugin-slots?slot=page").json()["items"]
    assert {"Chấm công", "Phiếu lương", "Sổ văn bản", "Sổ văn bản đến", "Văn bản chờ ký", "Tính hạn giải quyết"} <= {p["title"] for p in pages}
    packaged_page = next(p for p in pages if p["plugin_id"] == "vn.mo-rong.tinh-han")
    assert staff.get(packaged_page["url"]).status_code == 200
    actions = {p["title"] for p in staff.get(API + "/plugin-slots?slot=case.action").json()["items"]}
    assert {"Đọc giấy tờ", "Ký số", "Cấp số văn bản", "Vào sổ văn bản đến"} <= actions
    gps = next(p for p in pages if p["plugin_id"] == "vn.mo-rong.cham-cong")
    assert gps["allow"] == "geolocation"
    triggers = {t["key"] for t in as_(world, "director").get(API + "/automations/catalog").json()["triggers"]}
    assert {"plugin.vn.mo-rong.cham-cong.di_muon", "plugin.vn.mo-rong.tiep-nhan.ho_so_truc_tuyen",
            "plugin.vn.mo-rong.nhac-han.sap_het_han"} <= triggers  # fmt: skip


def install_connected(env, name, tmp_path, **extra):
    director = as_(env, "director")
    manifest = dong_goi.manifest(name)
    installed = upload(director, "/plugins", f"{name}.json", json.dumps(manifest).encode(), "application/json")
    approved = approve(director, manifest["id"], installed.json()["revision"], manifest, **extra)
    return connect(env, name, approved["issued"], tmp_path), manifest


def node(node_id, kind, **data):
    return {"id": node_id, "type": kind, "position": {"x": 0, "y": 0}, "data": data}


def enable_flow(env, name, graph):
    director = as_(env, "director")
    rule = director.post(API + "/automations", json={"name": name, "graph": graph})
    assert rule.status_code == 201, rule.text
    on = director.post(f"{API}/automations/{rule.json()['id']}/enabled",
                       json={"expected_revision": rule.json()["revision"], "enabled": True})  # fmt: skip
    assert on.status_code == 200, on.text


def submitted_case(env, key):
    from test_workspace import make_case, make_form

    case = make_case(env, make_form(env), key=key)
    response = as_(env, "staff").post(f"{API}/cases/{case['id']}/submit", json={"expected_revision": case["revision"]},
                                        headers={"Idempotency-Key": key + "-s"})  # fmt: skip
    assert response.status_code == 202, response.text
    drain(env, rounds=40)
    return case


def titles(env):
    return [n["title"] for n in as_(env, "staff").get(API + "/notifications").json()["items"]]


def test_flows_number_and_sign_documents_through_the_plugin_servers(world, tmp_path):  # noqa: F811
    world[8].plugin_allowed_hosts = "localhost"
    register, _ = install_connected(world, "so-van-ban", tmp_path)
    signer, _ = install_connected(world, "ky-so", tmp_path)
    serve({9203: register, 9204: signer})
    graph = {
        "nodes": [
            node("start", "trigger", event="case.submitted"),
            node("cap", "plugin_action", plugin_id="vn.mo-rong.so-van-ban", node="cap_so_van_ban",
                 config={"so": "GXN", "trich_yeu": "{title}"}, outputs={"so_van_ban": "Số"}),
            node("ky", "plugin_action", plugin_id="vn.mo-rong.ky-so", node="ky_so_van_ban", mode="async", config={}),
            node("bao", "notify", recipients=["owner"], title="Đã ký văn bản số {cap.so_van_ban}"),
        ],
        "edges": [
            {"id": "a", "source": "start", "target": "cap"},
            {"id": "b", "source": "cap", "target": "ky", "branch": "success"},
            {"id": "c", "source": "ky", "target": "bao", "branch": "success"},
        ],
    }  # fmt: skip
    enable_flow(world, "Cấp số và ký", graph)
    # The signer's key is an organisation setting kept (encrypted) by Desktiny.
    director = as_(world, "director")
    saved = director.put(f"{API}/plugins/vn.mo-rong.ky-so/settings", json={"expected_revision": 0, "values": {"khoa_ky": "khoa-thu"}})
    assert saved.status_code == 200, saved.text
    uploaded = as_(world, "staff").post(API + "/drive/files", files={"file": ("to-trinh.pdf", b"%PDF-1.4 to trinh", "application/pdf")},
                                         headers={"Idempotency-Key": "up-tt"}).json()  # fmt: skip
    from test_workspace import make_case, make_form

    case = make_case(world, make_form(world), key="ky-1", files=[uploaded["id"]])
    as_(world, "staff").post(f"{API}/cases/{case['id']}/submit", json={"expected_revision": case["revision"]},
                             headers={"Idempotency-Key": "ky-1-s"})  # fmt: skip
    drain(world, rounds=40)
    assert register.store.one("SELECT full_number FROM entries")["full_number"] == "1/GXN-UBND"
    request = signer.store.one("SELECT * FROM requests")
    assert request["state"] == "waiting" and request["case_id"] == case["id"]
    # The signer works on the page with a frame session, as the person they are.
    session = as_(world, "director").post(API + "/plugin-sessions", json={"plugin_id": "vn.mo-rong.ky-so", "slot": "page"}).json()
    headers = {"X-Desktiny-Session": session["token"], "Content-Type": "application/json"}
    assert signer.handle("POST", "/api/pin", headers, json.dumps({"pin": "246810"}).encode()).status == 200
    waiting = signer.handle("GET", "/api/cho-ky", headers).data["items"]
    assert [f["name"] for f in waiting[0]["files"]] == ["to-trinh.pdf"]
    signed = signer.handle("POST", f"/api/cho-ky/{request['call_id']}", headers, json.dumps({"pin": "246810"}).encode())
    assert signed.status == 200, signed.body
    drain(world, rounds=40)
    assert "Đã ký văn bản số 1/GXN-UBND" in titles(world)
    files = [f["name"] for f in as_(world, "staff").get(f"{API}/cases/{case['id']}").json()["files"]]
    assert any(name.startswith("xac-nhan-ky-so") for name in files)
    code = signed.data["codes"][0]
    assert signer.handle("GET", f"/xac-thuc/{code}").data["valid"] is True
    desktiny_plugins.use_transport(None)


def test_an_online_request_starts_a_flow_that_creates_the_dossier(world, tmp_path):  # noqa: F811
    world[8].plugin_allowed_hosts = "localhost"
    intake, _ = install_connected(world, "tiep-nhan", tmp_path)
    serve({9206: intake})
    from test_workspace import make_form

    form = make_form(world)
    # The intake form needs a field for the tracking code; the test form gets one through a new form.
    director = as_(world, "director")
    created = director.post(API + "/forms", json={"name": "Yêu cầu trực tuyến", "fields": [
        {"key": "reason", "label": "Nội dung", "type": "textarea", "required": True},
        {"key": "ma_tra_cuu", "label": "Mã tra cứu", "type": "text"}],
        "approval_steps": [{"label": "Duyệt", "resolver": "user", "user_id": world[7]["manager"]}]})  # fmt: skip
    assert created.status_code == 201, created.text
    graph = {
        "nodes": [
            node("start", "trigger", event="plugin.vn.mo-rong.tiep-nhan.ho_so_truc_tuyen"),
            node("tao", "create_case", form_id=created.json()["id"], title="{trigger.thu_tuc} — {trigger.ho_ten}",
                 answers={"reason": "{trigger.noi_dung}", "ma_tra_cuu": "{trigger.ma_tra_cuu}"}),
        ],
        "edges": [{"id": "a", "source": "start", "target": "tao"}],
    }  # fmt: skip
    enable_flow(world, "Tạo hồ sơ từ yêu cầu trực tuyến", graph)
    import re

    info = intake.handle("GET", "/cong/api/thong-tin").data
    a, b = map(int, re.findall(r"\d+", info["cau_hoi"]["noi_dung"]))
    body = {"thu_tuc": "Đăng ký khai sinh", "ho_ten": "Phạm Thị Hoa", "so_cccd": "001190012345", "so_dien_thoai": "0912345678",
            "noi_dung": "Khai sinh cho con", "cau_hoi_id": info["cau_hoi"]["id"], "tra_loi": str(a + b)}  # fmt: skip
    filed = intake.handle("POST", "/cong/api/nop", {"Content-Type": "application/json"}, json.dumps(body).encode())
    assert filed.status == 200, filed.body
    drain(world, rounds=40)
    staff_cases = as_(world, "director").get(API + "/cases?limit=50").json()["items"]
    made = [c for c in staff_cases if c["title"] == "Đăng ký khai sinh — Phạm Thị Hoa"]
    assert made, [c["title"] for c in staff_cases]
    assert form  # the usual test form exists alongside
    # The dossier carries the tracking code the plugin matches Desktiny's later events with (unit tests cover that).
    detail = as_(world, "director").get(f"{API}/cases/{made[0]['id']}").json()
    assert detail["payload"]["ma_tra_cuu"] == filed.data["ma_tra_cuu"]
    desktiny_plugins.use_transport(None)


def test_an_incoming_document_is_registered_by_its_flow_and_shown_on_the_document(world, tmp_path):  # noqa: F811
    world[8].plugin_allowed_hosts = "localhost"
    incoming, _ = install_connected(world, "so-van-ban-den", tmp_path)
    serve({9207: incoming})
    director = as_(world, "director")
    form = director.post(API + "/forms", json={"name": "Phiếu vào sổ văn bản đến", "fields": [
        {"key": "noi_gui", "label": "Nơi gửi", "type": "text", "required": True},
        {"key": "trich_yeu", "label": "Trích yếu", "type": "textarea", "required": True},
        {"key": "han_xu_ly", "label": "Hạn xử lý", "type": "date"},
        {"key": "so_den", "label": "Số đến", "type": "text"},
        {"key": "ngay_den", "label": "Ngày đến", "type": "date"}],
        "approval_steps": [{"label": "Lãnh đạo", "resolver": "user", "user_id": world[7]["manager"]}]})  # fmt: skip
    assert form.status_code == 201, form.text
    graph = {
        "nodes": [node("start", "trigger", event="case.submitted"),
                  node("vao_so", "plugin_action", plugin_id="vn.mo-rong.so-van-ban-den", node="vao_so_van_ban_den", config={},
                       outputs={"so_den": "Số đến", "ngay_den": "Ngày đến"}),
                  # Desktiny lets a plugin write form fields only in a person's session: the flow writes them itself.
                  node("ghi", "update_record", changes=[{"field": "form.so_den", "value": "{vao_so.so_den}"},
                                                         {"field": "form.ngay_den", "value": "{vao_so.ngay_den}"}]),
                  node("bao", "notify", recipients=["owner"], title="Đã vào sổ, số đến {vao_so.so_den}")],
        "edges": [{"id": "a", "source": "start", "target": "vao_so"}, {"id": "b", "source": "vao_so", "target": "ghi", "branch": "success"},
                  {"id": "c", "source": "ghi", "target": "bao"}],
    }  # fmt: skip
    enable_flow(world, "Vào sổ văn bản đến", graph)
    staff = as_(world, "staff")
    case = staff.post(API + "/cases", json={"title": "Công văn của Sở Nội vụ", "form_id": form.json()["id"],
                                            "payload": {"noi_gui": "Sở Nội vụ", "trich_yeu": "Về việc báo cáo văn thư",
                                                        "han_xu_ly": "2099-01-15"}},
                      headers={"Idempotency-Key": "den-1"}).json()  # fmt: skip
    submitted = staff.post(f"{API}/cases/{case['id']}/submit", json={"expected_revision": case["revision"]},
                           headers={"Idempotency-Key": "den-1-s"})  # fmt: skip
    assert submitted.status_code == 202, submitted.text
    drain(world, rounds=40)
    entry = incoming.store.one("SELECT * FROM entries")
    assert entry["number"] == 1 and entry["sender"] == "Sở Nội vụ" and entry["due"] == "2099-01-15"
    assert "Đã vào sổ, số đến 1" in titles(world)
    payload = as_(world, "director").get(f"{API}/cases/{case['id']}").json()["payload"]
    assert payload["so_den"] == "1" and payload["ngay_den"] == entry["received_at"][:10]
    # The side panel, as the person looking at the document.
    session = as_(world, "staff").post(API + "/plugin-sessions", json={"plugin_id": "vn.mo-rong.so-van-ban-den", "slot": "case.side",
                                                                    "case_id": case["id"]}).json()  # fmt: skip
    shown = incoming.handle("GET", f"/api/van-ban/{case['id']}", {"X-Desktiny-Session": session["token"]})
    assert shown.status == 200, shown.body
    assert shown.data["entry"]["status"] == "open"
    desktiny_plugins.use_transport(None)


def test_a_sensor_past_its_threshold_becomes_an_incident_dossier_for_the_configured_person(world, tmp_path):  # noqa: F811
    world[8].plugin_allowed_hosts = "localhost"
    sensors, manifest = install_connected(world, "cam-bien", tmp_path)
    serve({9208: sensors})
    director = as_(world, "director")
    files = dong_goi.pack_files("van-hanh")
    installed = upload(director, "/packs", "van-hanh.zip", dong_goi.zipped(files))
    assert installed.status_code == 201, installed.text
    rule = next(r for r in director.get(API + "/automations?limit=200").json()["items"] if r["name"] == "Xử lý sự cố thiết bị")
    template = json.loads(files["templates/su-co-cam-bien.json"])
    graph = template["graph"]
    graph["nodes"][1]["data"]["form_id"] = rule["form_id"]  # what the organisation picks on the canvas
    enable_flow(world, template["title"], graph)
    staff_name = next(u["display_name"] for u in director.get(API + "/users").json()["items"] if u["id"] == world[7]["staff"])
    saved = director.put(f"{API}/plugins/{manifest['id']}/settings",
                         json={"expected_revision": 0, "values": {"nguong": "nhiet_do>80", "nguoi_phu_trach": staff_name}})  # fmt: skip
    assert saved.status_code == 200, saved.text
    session = director.post(API + "/plugin-sessions", json={"plugin_id": manifest["id"], "slot": "admin.page"}).json()
    added = sensors.handle("POST", "/api/quan-tri/thiet-bi", {"X-Desktiny-Session": session["token"]},
                           json.dumps({"ma": "lo-say-1", "ten": "Lò sấy số 1"}).encode())  # fmt: skip
    assert added.status == 200, added.body
    headers = {"X-Device-Key": added.data["khoa"], "Content-Type": "application/json"}
    for value in (70, 92, 95):
        sent = sensors.handle("POST", "/api/so-do", headers, json.dumps({"thiet_bi": "lo-say-1", "chi_so": "nhiet_do", "gia_tri": value}).encode())
        assert sent.status == 200, sent.body
    drain(world, rounds=40)
    made = [c for c in director.get(API + "/cases?limit=50").json()["items"] if c["title"].startswith("Sự cố Lò sấy số 1")]
    assert len(made) == 1, [c["title"] for c in made]  # 92 and 95 are the same incident
    case = director.get(f"{API}/cases/{made[0]['id']}").json()
    assert case["payload"]["gia_tri"] == 92 and case["payload"]["nguoi_phu_trach"] == staff_name
    assert case["status"] == "draft" and case["owner_id"] == world[7]["director"]  # for the flow's owner to check and submit
    # Submitted with that payload, the process asks the person the plugin's settings name. (A draft made by a flow
    # cannot be submitted in this in-memory Desktiny: its Core record is not granted to the owner, so the same payload
    # goes through a dossier made by hand.)
    payload = {k: v for k, v in case["payload"].items() if v not in (None, "")}
    filed = director.post(API + "/cases", json={"title": case["title"], "form_id": rule["form_id"], "payload": payload},
                          headers={"Idempotency-Key": "su-co"}).json()  # fmt: skip
    submitted = director.post(f"{API}/cases/{filed['id']}/submit", json={"expected_revision": filed["revision"]},
                              headers={"Idempotency-Key": "su-co-s"})  # fmt: skip
    assert submitted.status_code == 202, submitted.text
    drain(world, rounds=40)
    asked = as_(world, "staff").get(API + "/approval-tasks").json()["items"]
    assert [t for t in asked if t.get("case_id") == filed["id"]], asked
    desktiny_plugins.use_transport(None)


@pytest.mark.skipif(not hasattr(desktiny_automations, "ending_outcome"),
                    reason="Desktiny này chưa có bản sửa B1 (nhánh hết bước thì hồ sơ kết thúc); 3.1.0 còn kẹt hồ sơ.")
def test_a_pack_dossier_whose_flow_ends_with_a_notice_closes_once_approved(world):  # noqa: F811
    """B1: the packs end their processes with a notice ("Báo người nộp"), not an ending step; the dossier must still
    close after the last approval instead of staying "đang xử lý" for good."""
    director = as_(world, "director")
    files = dong_goi.pack_files("mot-cua-xa")
    assert upload(director, "/packs", "mot-cua-xa.zip", dong_goi.zipped(files)).status_code == 201
    staff = as_(world, "staff")
    process = next(p for p in staff.get(API + "/processes/available").json()["items"] if p["name"] == "Đăng ký khai sinh")
    payload = {"ho_ten": "Phạm Thị Hoa", "so_cccd": "001190012345", "ho_ten_tre": "Phạm Minh An", "ngay_sinh_tre": "2026-11-20",
               "gioi_tinh_tre": "Nam", "noi_sinh": "Trạm y tế xã", "quan_he": "Mẹ"}  # fmt: skip
    case = staff.post(API + "/cases", json={"title": "Khai sinh cho Phạm Minh An", "form_id": process["form_id"],
                                            "process_id": process["id"], "payload": payload},
                      headers={"Idempotency-Key": "khai-sinh-b1"})  # fmt: skip
    assert case.status_code == 201, case.text
    case = case.json()
    submitted = staff.post(f"{API}/cases/{case['id']}/submit", json={"expected_revision": case["revision"]},
                           headers={"Idempotency-Key": "khai-sinh-b1-s"})  # fmt: skip
    assert submitted.status_code == 202, submitted.text
    drain(world, rounds=40)
    for who in ("manager", "director"):  # công chức tư pháp kiểm tra (trưởng đơn vị), rồi lãnh đạo UBND ký
        client = as_(world, who)
        task = client.get(API + "/approval-tasks").json()["items"][0]
        decided = client.post(f"{API}/approval-tasks/{task['id']}/decisions",
                              json={"expected_revision": task["revision"], "decision": "approve", "reason": ""},
                              headers={"Idempotency-Key": f"khai-sinh-b1-{who}"})  # fmt: skip
        assert decided.status_code in (200, 202), decided.text
        drain(world, rounds=40)
    assert staff.get(f"{API}/cases/{case['id']}").json()["status"] == "approved"
    assert any(title.startswith("Đã có kết quả, mời đến nhận") for title in titles(world))
