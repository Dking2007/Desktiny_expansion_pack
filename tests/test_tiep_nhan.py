# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import re

from conftest import call, signed

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
