# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import re
from datetime import datetime

from conftest import call, load, signed

PERSON = {"thu_tuc": "Đăng ký khai sinh", "ho_ten": "Phạm Thị Hoa", "so_cccd": "001190012345",
          "so_dien_thoai": "0912345678", "dia_chi": "Thôn Đông", "noi_dung": "Khai sinh cho con"}  # fmt: skip


def answer(app):
    info = app.handle("GET", "/cong/api/thong-tin").data
    a, b = map(int, re.findall(r"\d+", info["cau_hoi"]["noi_dung"]))
    return info, {"cau_hoi_id": info["cau_hoi"]["id"], "tra_loi": str(a + b)}


def test_a_citizen_files_and_follows_a_request_as_the_dossier_moves(make_app, desktiny):
    app = make_app("tiep-nhan")
    info, check = answer(app)
    assert "Đăng ký khai sinh" in info["thu_tuc"]
    wrong = call(app, "POST", "/cong/api/nop", {**PERSON, "cau_hoi_id": check["cau_hoi_id"], "tra_loi": "99"})
    assert wrong.status == 422 and wrong.data["error"] == "challenge_failed"
    _, check = answer(app)
    bad_id = call(app, "POST", "/cong/api/nop", {**PERSON, **check, "so_cccd": "123"})
    assert bad_id.status == 422
    _, check = answer(app)
    filed = call(app, "POST", "/cong/api/nop", {**PERSON, **check})
    assert filed.status == 200, filed.body
    code, secret = filed.data["ma_tra_cuu"], filed.data["ma_bi_mat"]
    event = [c for c in desktiny.calls if c[0] == "send_event"][0]
    assert event[2][0] == "ho_so_truc_tuyen" and event[2][1]["ma_tra_cuu"] == code and event[3]["key"] == f"nop:{code}"
    assert app.handle("GET", f"/cong/api/tra-cuu?ma={code}&ma_bi_mat=000000").status == 404
    # The flow created the dossier with the tracking code; Desktiny reports its progress.
    desktiny.cases["hs-7"] = {"id": "hs-7", "code": "HS-000007", "title": "Khai sinh", "status": "processing",
                              "payload": {"ma_tra_cuu": code}}  # fmt: skip
    for kind in ("case.submitted", "case.needs_revision", "case.approved"):
        assert signed(app, "/events", {"type": kind, "subject": {"type": "case", "id": "hs-7"}}).status == 202
    tracked = app.handle("GET", f"/cong/api/tra-cuu?ma={code.lower()}&ma_bi_mat={secret}").data
    assert tracked["trang_thai"].startswith("Đã có kết quả") and tracked["ma_ho_so"] == "HS-000007"
    assert [h["trang_thai"][:7] for h in tracked["lich_su"]] == ["Đã nhận", "Đang xử", "Cần bổ ", "Đã có k"]
    assert "ho_ten" not in tracked and "Phạm" not in str(tracked)  # no personal data in the public answer
    side = call(app, "GET", "/api/ho-so/hs-7", session="phien-an").data["request"]
    assert side["code"] == code and side["source"] == "cổng trực tuyến"
    assert call(app, "GET", "/api/quan-tri", session="phien-an").status == 403
    assert len(call(app, "GET", "/api/quan-tri", session="phien-qt").data["items"]) == 1


def test_outside_systems_need_the_key_and_the_page_limits_repeats(make_app, desktiny):
    app = make_app("tiep-nhan")
    assert app.handle("POST", "/api/ngoai/ho-so", {"X-Api-Key": "x"}, b"{}").status == 401
    desktiny.settings = {"khoa_he_thong_ngoai": "khoa-ki-ot"}
    app.forget_settings()
    import json

    sent = app.handle("POST", "/api/ngoai/ho-so", {"X-Api-Key": "khoa-ki-ot"}, json.dumps({**PERSON, "nguon": "Ki-ốt"}).encode())
    assert sent.status == 200 and sent.data["ma_tra_cuu"].startswith("TN-")
    for _ in range(5):
        _, check = answer(app)
        assert call(app, "POST", "/cong/api/nop", {**PERSON, **check}).status == 200
    _, check = answer(app)
    assert call(app, "POST", "/cong/api/nop", {**PERSON, **check}).status == 429
    assert app.handle("GET", "/cong/nop.html").status == 200


def test_the_citizen_gets_a_guide_and_an_expected_date_and_the_lookup_still_shows_nothing_personal(make_app, desktiny):
    module = load("tiep-nhan")
    friday = lambda: datetime(2026, 11, 27, 9, 30, tzinfo=module.VN)  # noqa: E731
    app = make_app("tiep-nhan", now=friday)
    info, check = answer(app)
    guide = info["huong_dan"]["Đăng ký khai sinh"]
    assert guide["thoi_han"] and any("chứng sinh" in paper for paper in guide["giay_to"])
    assert set(info["huong_dan"]) <= set(info["thu_tuc"])
    filed = call(app, "POST", "/cong/api/nop", {**PERSON, **check}).data
    # Filed on a Friday: one working day later is the Monday.
    assert filed["hen_tra"] == "2026-11-30" and filed["ngay_nop"].startswith("2026-11-27") and filed["giay_to"] == guide["giay_to"]
    assert module.expected("Xác nhận tình trạng hôn nhân", "2026-11-26T10:00:00+07:00") == "2026-12-01"
    assert module.expected("Đề nghị hoà giải", "2026-11-26") is None and module.expected("Thủ tục riêng", "2026-11-26") is None
    code, secret = filed["ma_tra_cuu"], filed["ma_bi_mat"]
    tracked = app.handle("GET", f"/cong/api/tra-cuu?ma={code}&ma_bi_mat={secret}").data
    assert tracked["trang_thai_ma"] == "received" and tracked["hen_tra"] == "2026-11-30"
    assert tracked["co_quan"] == "Bộ phận Một cửa" and [h["ma"] for h in tracked["lich_su"]] == ["received"]
    for private in ("Phạm", PERSON["so_cccd"], PERSON["so_dien_thoai"], "Thôn Đông", "Khai sinh cho con"):
        assert private not in str(tracked)
    desktiny.cases["hs-8"] = {"id": "hs-8", "code": "HS-000008", "status": "processing", "payload": {"ma_tra_cuu": code}}
    signed(app, "/events", {"type": "case.submitted", "subject": {"type": "case", "id": "hs-8"}})
    side = call(app, "GET", "/api/ho-so/hs-8", session="phien-an").data["request"]
    assert side["full_name"] == "Phạm Thị Hoa" and side["phone"] == "0912345678" and side["expected"] == "2026-11-30"
    assert [h["status"] for h in side["history"]] == ["received", "processing"] and side["history"][1]["label"] == "Đang xử lý"
    admin = call(app, "GET", "/api/quan-tri", session="phien-qt").data
    assert admin["today"] == "2026-11-27" and admin["items"][0]["expected"] == "2026-11-30"
    assert admin["items"][0]["case_code"] == "HS-000008" and "updated_at" in admin["items"][0]
    assert call(app, "GET", "/api/quan-tri?trang_thai=received", session="phien-qt").data["items"] == []


def test_the_portal_root_leads_to_the_filing_page(make_app):
    app = make_app("tiep-nhan")
    for path in ("/cong", "/cong/"):
        page = call(app, "GET", path)
        assert page.status == 302 and page.headers["Location"] == "/cong/nop.html", path
