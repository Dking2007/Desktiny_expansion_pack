# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
from datetime import date

from conftest import call, signed


def dossier(case_id, expires, owner="u-an", status="approved"):
    return {"id": case_id, "code": f"HS-{case_id}", "title": f"Hợp đồng {case_id}", "status": status,
            "form": {"id": "f-hd"}, "owner": {"id": owner, "display_name": "x"}, "payload": {"ngay_het_han": expires}}  # fmt: skip


def test_each_threshold_is_reminded_once_and_announced(make_app, desktiny):
    today = {"value": date(2026, 11, 1)}
    app = make_app("nhac-han", today=lambda: today["value"])
    desktiny.cases = {"a": dossier("a", "2026-11-30"), "b": dossier("b", "2027-06-01"), "c": dossier("c", "")}
    assert app.round() == {"read": 3, "reminded": 1}  # a: 29 days left → the 30-day mark
    assert app.round()["reminded"] == 0
    today["value"] = date(2026, 11, 24)  # 6 days left: the 7-day mark, once
    assert app.round()["reminded"] == 1
    events = [c for c in desktiny.calls if c[0] == "send_event"]
    assert events[-1][2] == ("sap_het_han", {"ho_so": "a", "ngay_het_han": "2026-11-30", "con_lai": 6})
    notices = [c for c in desktiny.calls if c[0] == "notify"]
    assert notices[0][2][1] == ["u-an"] and "còn 29 ngày" in notices[0][2][0]
    # A renewed contract moves its date; a cancelled one stops being watched.
    desktiny.cases["a"] = dossier("a", "2027-11-30")
    desktiny.cases["b"] = dossier("b", "2027-06-01", status="cancelled")
    app.round()
    rows = call(app, "GET", "/api/quan-tri?ngay=900", session="phien-qt").data
    assert [r["case_id"] for r in rows["items"]] == ["a"] and rows["watched"] == 1


def test_people_and_the_assistant_see_only_dossiers_they_may_open(make_app, desktiny):
    app = make_app("nhac-han", today=lambda: date(2026, 11, 1))
    desktiny.cases = {"a": dossier("a", "2026-11-10")}
    app.round()
    assert [r["case_id"] for r in call(app, "GET", "/api/sap-het-han", session="phien-an").data["items"]] == ["a"]
    del desktiny.cases["a"]  # this person (the fake) can no longer open it
    assert call(app, "GET", "/api/sap-het-han", session="phien-an").data["items"] == []
    desktiny.cases = {"a": dossier("a", "2026-11-10")}
    tool = signed(app, "/tools/sap-het-han", {"arguments": {"so_ngay": 30}, "token": "phien-an", "user": {"id": "u-an"}})
    assert tool.data["result"][0]["con_lai_ngay"] == 9


def test_admin_overview_shows_bands_and_reminders_already_sent(make_app, desktiny):
    today = {"value": date(2026, 11, 1)}
    app = make_app("nhac-han", today=lambda: today["value"])
    desktiny.cases = {"qua": dossier("qua", "2026-10-20"), "gan": dossier("gan", "2026-11-05"),
                      "thang": dossier("thang", "2026-11-25"), "quy": dossier("quy", "2027-01-15"),
                      "xa": dossier("xa", "2027-09-01")}  # fmt: skip
    app.round()
    today["value"] = date(2026, 11, 3)  # "gan": 2 days left, now the 7-day mark
    app.round()
    data = call(app, "GET", "/api/quan-tri", session="phien-qt").data
    assert data["counts"] == {"overdue": 1, "d7": 1, "d30": 1, "d90": 1, "later": 1}
    assert data["marks"] == [30, 7, 1, 0] and data["today"] == "2026-11-03" and data["truncated"] is False
    by_id = {item["case_id"]: item for item in data["items"]}
    assert set(by_id) == {"qua", "gan", "thang", "quy"}  # 90 days ahead by default
    assert [m["mark"] for m in by_id["gan"]["reminded"]] == [7]  # the 30-day mark was sent on day one
    assert by_id["quy"]["reminded"] == []
    assert [m["mark"] for m in by_id["thang"]["reminded"]] == [30] and by_id["thang"]["reminded"][0]["at"] == "2026-11-01"
    # A renewed date starts a fresh set of reminders.
    desktiny.cases["gan"] = dossier("gan", "2026-12-01")
    app.round()
    gan = next(i for i in call(app, "GET", "/api/quan-tri", session="phien-qt").data["items"] if i["case_id"] == "gan")
    assert gan["expires"] == "2026-12-01" and [m["mark"] for m in gan["reminded"]] == [30]


def test_the_admin_overview_is_for_the_admin_page_only(make_app, desktiny):
    app = make_app("nhac-han", today=lambda: date(2026, 11, 1))
    desktiny.cases = {"a": dossier("a", "2026-11-10")}
    app.round()
    assert call(app, "GET", "/api/quan-tri", session="phien-an").status == 403
    assert call(app, "POST", "/api/quan-tri/quet", body={}, session="phien-an").status == 403
    mine = call(app, "GET", "/api/sap-het-han", session="phien-an").data
    assert mine["marks"] == [30, 7, 1, 0] and "reminded" not in mine["items"][0] and "counts" not in mine
