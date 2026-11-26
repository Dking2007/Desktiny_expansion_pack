# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import hashlib
from datetime import datetime, timedelta, timezone

from conftest import call, signed


def setup(desktiny):
    desktiny.settings = {"khoa_ky": "khoa-cua-co-quan-rat-dai"}
    desktiny.cases["hs-1"] = {"id": "hs-1", "code": "HS-000001", "title": "Giấy xác nhận tình trạng hôn nhân", "payload": {}}
    desktiny.files["tep-1"] = ("hs-1", "giay-xac-nhan.pdf", b"%PDF-1.4 noi dung")


def test_a_flow_waits_for_the_signer_who_signs_with_a_pin_and_anyone_can_verify(make_app, desktiny):
    setup(desktiny)
    app = make_app("ky-so")
    queued = signed(app, "/nodes/ky-so", {"call_id": "goi-1", "node_id": "ky", "subject": {"type": "case", "id": "hs-1"},
                                         "config": {"nguoi_ky": "u-binh"}})  # fmt: skip
    assert queued.status == 202
    assert [c for c in desktiny.calls if c[0] == "notify"][0][2][1] == ["u-binh"]
    assert call(app, "GET", "/api/cho-ky", session="phien-an").data["items"] == []  # not An's to sign
    waiting = call(app, "GET", "/api/cho-ky", session="phien-binh").data["items"]
    assert waiting[0]["files"][0]["name"] == "giay-xac-nhan.pdf"
    no_pin = call(app, "POST", "/api/cho-ky/goi-1", {"pin": "123456"}, "phien-binh")
    assert no_pin.status == 409
    assert call(app, "POST", "/api/pin", {"pin": "12"}, "phien-binh").status == 422
    assert call(app, "POST", "/api/pin", {"pin": "246810"}, "phien-binh").status == 200
    assert call(app, "POST", "/api/cho-ky/goi-1", {"pin": "000000"}, "phien-binh").status == 403
    done = call(app, "POST", "/api/cho-ky/goi-1", {"pin": "246810"}, "phien-binh")
    assert done.status == 200 and done.data["signed"] == 1, done.body
    attach = [c for c in desktiny.calls if c[0] == "attach"][0]
    assert attach[1] == "cai-dat" and attach[3]["node_id"] == "ky" and attach[2][2].startswith(b"%PDF")
    complete = [c for c in desktiny.calls if c[0] == "complete_call"][0]
    assert complete[2][0:2] == ("goi-1", "success") and complete[2][2]["nguoi_ky"] == "Trần Thị Bình"
    check = app.handle("GET", f"/xac-thuc/{done.data['codes'][0].lower()}")
    assert check.data["valid"] is True and check.data["sha256"] == hashlib.sha256(b"%PDF-1.4 noi dung").hexdigest()
    assert app.handle("GET", "/xac-thuc/KHONGCO").status == 404
    assert call(app, "GET", "/api/cho-ky", session="phien-binh").data["items"] == []
    page = app.handle("GET", "/cong/xac-thuc.html")
    assert page.status == 200 and page.content_type.startswith("text/html")


def test_the_dossier_button_signs_now_and_a_refusal_takes_the_error_exit(make_app, desktiny):
    setup(desktiny)
    app = make_app("ky-so")
    call(app, "POST", "/api/pin", {"pin": "135790"}, "phien-an")
    now = call(app, "POST", "/api/ho-so/hs-1/ky", {"pin": "135790"}, "phien-an")
    assert now.status == 200 and [c for c in desktiny.calls if c[0] == "attach"][0][1] == "phien-an"
    signed(app, "/nodes/ky-so", {"call_id": "goi-2", "node_id": "ky", "subject": {"type": "case", "id": "hs-1"}, "config": {}})
    refused = call(app, "POST", "/api/cho-ky/goi-2", {"pin": "135790", "tu_choi": True, "ly_do": "Sai thông tin"}, "phien-an")
    assert refused.data["state"] == "refused"
    assert [c for c in desktiny.calls if c[0] == "complete_call"][-1][2][1:4:2] == ("error", "Sai thông tin")
    for _ in range(5):
        call(app, "POST", "/api/ho-so/hs-1/ky", {"pin": "000000"}, "phien-an")
    assert call(app, "POST", "/api/ho-so/hs-1/ky", {"pin": "135790"}, "phien-an").status == 423


def test_the_queue_shows_the_dossier_code_and_deadline_and_a_signature_names_each_file_and_code(make_app, desktiny):
    setup(desktiny)
    desktiny.files["tep-2"] = ("hs-1", "to-khai.pdf", b"%PDF-1.4 to khai")
    app = make_app("ky-so", now=lambda: datetime(2026, 11, 20, 8, 30, tzinfo=timezone(timedelta(hours=7))))
    signed(app, "/nodes/ky-so", {"call_id": "goi-3", "node_id": "ky", "subject": {"type": "case", "id": "hs-1"}, "config": {}})
    item = call(app, "GET", "/api/cho-ky", session="phien-an").data["items"][0]
    assert item["case_code"] == "HS-000001" and item["due_at"] == "2026-11-25T08:30:00+07:00"  # the step's 5 days
    call(app, "POST", "/api/pin", {"pin": "135790"}, "phien-an")
    done = call(app, "POST", "/api/cho-ky/goi-3", {"pin": "135790", "file_ids": ["tep-2"]}, "phien-an").data
    assert done["files"] == [{"name": "to-khai.pdf", "code": done["codes"][0]}]
    dossier = call(app, "GET", "/api/ho-so/hs-1", session="phien-an").data
    assert dossier["case"]["code"] == "HS-000001"
    signatures = dossier["signatures"]
    assert [(s["file_id"], s["code"]) for s in signatures] == [("tep-2", done["codes"][0])]
