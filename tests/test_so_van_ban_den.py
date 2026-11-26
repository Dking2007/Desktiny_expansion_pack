# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Sổ văn bản đến: one gapless series of số đến a year, written back into the document, tracked until it closes."""

import threading
from datetime import datetime, timedelta, timezone

from conftest import call, signed

VN = timezone(timedelta(hours=7))
FIELDS = [{"key": k} for k in ("noi_gui", "so_ky_hieu_goc", "trich_yeu", "do_khan", "han_xu_ly", "so_den", "ngay_den")]


def document(desktiny, case_id, **payload):
    desktiny.cases[case_id] = {
        "id": case_id, "title": f"Văn bản {case_id}", "status": "processing", "form": {"id": "f-den", "fields": FIELDS},
        "payload": {"noi_gui": "Sở Nội vụ", "so_ky_hieu_goc": "123/SNV-VP", "trich_yeu": "Về việc báo cáo công tác văn thư",
                    "do_khan": "Thường", **payload},
    }  # fmt: skip


def test_numbers_run_without_gaps_once_per_document_and_restart_each_year(make_app, desktiny):
    clock = {"now": datetime(2026, 12, 31, 9, 0, tzinfo=VN)}
    app = make_app("so-van-ban-den", now=lambda: clock["now"])
    document(desktiny, "vb-1", han_xu_ly="2027-01-05")
    first = call(app, "POST", "/api/van-ban/vb-1/vao-so", session="phien-an")
    assert first.status == 200 and first.data["entry"]["number"] == 1
    assert first.data["written"] == ["ngay_den", "so_den"]
    assert desktiny.cases["vb-1"]["payload"]["so_den"] == "1"
    assert desktiny.cases["vb-1"]["payload"]["ngay_den"] == "2026-12-31"
    again = call(app, "POST", "/api/van-ban/vb-1/vao-so", session="phien-binh")
    assert again.data["entry"]["id"] == first.data["entry"]["id"] and again.data["written"] == []
    # Many at once still get distinct, consecutive numbers.
    for i in range(15):
        document(desktiny, f"song-{i}")
    results = []
    threads = [threading.Thread(target=lambda i=i: results.append(
        call(app, "POST", f"/api/van-ban/song-{i}/vao-so", session="phien-an").data["entry"]["number"])) for i in range(15)]  # fmt: skip
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == list(range(2, 17))
    clock["now"] = datetime(2027, 1, 2, 8, 0, tzinfo=VN)
    document(desktiny, "vb-moi")
    assert call(app, "POST", "/api/van-ban/vb-moi/vao-so", session="phien-an").data["entry"]["number"] == 1


def test_a_document_without_sender_or_summary_is_refused_and_the_flow_step_numbers_it_too(make_app, desktiny):
    app = make_app("so-van-ban-den")
    document(desktiny, "vb-thieu", noi_gui="")
    refused = call(app, "POST", "/api/van-ban/vb-thieu/vao-so", session="phien-an")
    assert refused.status == 422 and "Cơ quan, tổ chức gửi" in refused.data["message"]
    assert signed(app, "/nodes/vao-so", {"subject": {"type": "case", "id": "vb-thieu"}}).data["branch"] == "error"
    document(desktiny, "vb-2", han_xu_ly="15/01/2027")
    step = signed(app, "/nodes/vao-so", {"run_id": "r", "node_id": "n", "subject": {"type": "case", "id": "vb-2"}}).data
    assert step["branch"] == "success" and step["output"]["so_den"] == "1" and step["output"]["han_xu_ly"] == "2027-01-15"
    # The install token may not write form fields; the flow's own "Cập nhật hồ sơ" step does that.
    assert not [c for c in desktiny.calls if c[0] == "write_fields"]
    assert call(app, "GET", "/api/van-ban/vb-2", session="phien-an").data["entry"]["registered_by"] == "Quy trình"
    assert signed(app, "/nodes/vao-so", {"subject": {"type": "task", "id": "x"}}).data["branch"] == "error"


def test_the_register_shows_due_soon_overdue_and_done_and_closing_the_document_ends_it(make_app, desktiny):
    clock = {"now": datetime(2026, 11, 20, 9, 0, tzinfo=VN)}
    app = make_app("so-van-ban-den", now=lambda: clock["now"])
    document(desktiny, "qua-han", han_xu_ly="2026-11-18", do_khan="Hoả tốc")
    document(desktiny, "sap-han", han_xu_ly="2026-11-21")
    document(desktiny, "con-lau", han_xu_ly="2026-12-30")
    for case_id in ("qua-han", "sap-han", "con-lau"):
        call(app, "POST", f"/api/van-ban/{case_id}/vao-so", session="phien-an")
    data = call(app, "GET", "/api/so", session="phien-an").data
    assert data["counts"] == {"open": 1, "due_soon": 1, "overdue": 1, "done": 0}
    widget = call(app, "GET", "/api/can-xu-ly", session="phien-an").data["items"]
    assert [r["case_id"] for r in widget][0] == "qua-han" and widget[0]["urgent"] and widget[0]["left"] == -2
    desktiny.cases["con-lau"]["status"] = "approved"
    assert signed(app, "/events", {"type": "case.closed", "subject": {"type": "case", "id": "con-lau"}}).status == 202
    done = call(app, "GET", "/api/so?tinh_trang=done", session="phien-an").data["entries"]
    assert [e["case_id"] for e in done] == ["con-lau"] and done[0]["outcome"] == "approved"
    overdue = signed(app, "/tools/van-ban-den", {"arguments": {"tinh_trang": "qua_han"}, "token": "phien-an"}).data["result"]
    assert [r["so_den"] for r in overdue] == [1] and overdue[0]["qua_han"] is True


def test_people_see_documents_they_may_open_and_only_managers_cancel_numbers(make_app, desktiny):
    app = make_app("so-van-ban-den")
    document(desktiny, "vb-an")
    document(desktiny, "vb-binh")
    call(app, "POST", "/api/van-ban/vb-an/vao-so", session="phien-an")
    entry = call(app, "POST", "/api/van-ban/vb-binh/vao-so", session="phien-binh").data["entry"]
    del desktiny.cases["vb-an"]  # An's document is no longer one Bình (the fake: anyone) may open
    seen = [e["case_id"] for e in call(app, "GET", "/api/so", session="phien-binh").data["entries"]]
    assert seen == ["vb-binh"]
    assert len(call(app, "GET", "/api/so", session="phien-qt").data["entries"]) == 2
    export = call(app, "GET", "/api/xuat", session="phien-binh").body.decode()
    assert "Sở Nội vụ" in export and export.count("\n") == 2  # header and Bình's one row
    assert call(app, "POST", f"/api/quan-tri/huy/{entry['id']}", {"ly_do": "Nhầm"}, "phien-binh").status == 403
    assert call(app, "POST", f"/api/quan-tri/huy/{entry['id']}", {}, "phien-qt").status == 422
    call(app, "POST", f"/api/quan-tri/huy/{entry['id']}", {"ly_do": "Vào sổ trùng"}, "phien-qt")
    document(desktiny, "vb-3")
    assert call(app, "POST", "/api/van-ban/vb-3/vao-so", session="phien-an").data["entry"]["number"] == 3  # 2 is not reused
    cancelled = call(app, "GET", "/api/so?tinh_trang=cancelled", session="phien-qt").data["entries"]
    assert [e["cancel_reason"] for e in cancelled] == ["Vào sổ trùng"]


def test_the_pages_see_the_number_to_come_the_deadline_as_set_later_and_the_years_of_the_register(make_app, desktiny):
    clock = {"now": datetime(2026, 11, 20, 9, 0, tzinfo=VN)}
    app = make_app("so-van-ban-den", now=lambda: clock["now"])
    document(desktiny, "vb-1", ngay_van_ban="2026-11-18", loai_van_ban="Công văn", nguoi_xu_ly="Trần Thị Bình")
    before = call(app, "GET", "/api/van-ban/vb-1", session="phien-an").data
    assert before["entry"] is None and before["next_number"] == 1 and before["today"] == "2026-11-20"
    assert before["deadline"] is None and before["bao_truoc_ngay"] == 2
    assert before["draft"]["nguoi_xu_ly"] == "Trần Thị Bình" and before["draft"]["loai_van_ban"] == "Công văn"
    assert call(app, "POST", "/api/van-ban/vb-1/vao-so", session="phien-an").data["entry"]["number"] == before["next_number"]
    # The leader sets the deadline after the document was registered: the dossier's own deadline is what shows.
    desktiny.cases["vb-1"]["payload"]["han_xu_ly"] = "21/11/2026"
    after = call(app, "GET", "/api/van-ban/vb-1", session="phien-an").data
    assert after["next_number"] is None and after["deadline"] == {"due": "2026-11-21", "left": 1, "status": "due_soon"}
    document(desktiny, "vb-2")
    assert call(app, "GET", "/api/van-ban/vb-2", session="phien-an").data["next_number"] == 2
    clock["now"] = datetime(2027, 1, 3, 9, 0, tzinfo=VN)
    register = call(app, "GET", "/api/so?nam=2026", session="phien-an").data
    assert register["years"] == [2027, 2026] and register["bao_truoc_ngay"] == 2
    assert call(app, "GET", "/api/can-xu-ly", session="phien-an").data["bao_truoc_ngay"] == 2


def test_the_admin_overview_shows_the_next_number_and_the_year_by_month_and_is_for_the_admin_page_only(make_app, desktiny):
    clock = {"now": datetime(2026, 3, 10, 9, 0, tzinfo=VN)}
    app = make_app("so-van-ban-den", now=lambda: clock["now"])
    desktiny.settings = {"bao_truoc_ngay": 4}
    for i, month in enumerate((3, 3, 5)):
        clock["now"] = datetime(2026, month, 10, 9, 0, tzinfo=VN)
        document(desktiny, f"vb-{i}")
        call(app, "POST", f"/api/van-ban/vb-{i}/vao-so", session="phien-an")
    entry_id = call(app, "GET", "/api/van-ban/vb-2", session="phien-an").data["entry"]["id"]
    call(app, "POST", f"/api/quan-tri/huy/{entry_id}", {"ly_do": "Vào sổ nhầm"}, "phien-qt")
    assert call(app, "GET", "/api/quan-tri/tong-quan", session="phien-an").status == 403
    data = call(app, "GET", "/api/quan-tri/tong-quan", session="phien-qt").data
    assert data["year"] == 2026 and data["next_number"] == 4 and data["cancelled"] == 1 and data["bao_truoc_ngay"] == 4
    assert data["months"][2] == 2 and sum(data["months"]) == 2 and data["years"] == [2026]
