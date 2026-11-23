# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import threading
from datetime import datetime, timedelta, timezone

from conftest import call, signed

VN = timezone(timedelta(hours=7))


def test_numbers_run_without_gaps_repeat_for_the_same_key_and_restart_each_year(make_app, desktiny):
    clock = {"now": datetime(2026, 12, 31, 9, 0, tzinfo=VN)}
    app = make_app("so-van-ban", now=lambda: clock["now"])
    first = signed(app, "/nodes/cap-so", {"run_id": "r1", "node_id": "cap", "config": {"so": "qd", "trich_yeu": "Khen thưởng"},
                                          "subject": {"type": "case", "id": "hs-1"}})  # fmt: skip
    assert first.data["output"]["so_van_ban"] == "1/QĐ-UBND"
    again = signed(app, "/nodes/cap-so", {"run_id": "r1", "node_id": "cap", "config": {"so": "QD"}})
    assert again.data["output"]["so"] == 1  # the same step asking again
    # Many at once still get distinct, consecutive numbers.
    results = []
    threads = [threading.Thread(target=lambda i=i: results.append(
        signed(app, "/nodes/cap-so", {"run_id": f"p{i}", "node_id": "cap", "config": {"so": "QD"}}).data["output"]["so"]))
        for i in range(20)]  # fmt: skip
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == list(range(2, 22))
    desktiny.settings = {"ky_hieu_co_quan": "UBND-VP"}
    app.forget_settings()
    letter = signed(app, "/nodes/cap-so", {"run_id": "r2", "node_id": "cap", "config": {"so": "CV"}})
    assert letter.data["output"]["so_van_ban"] == "1/UBND-VP"
    clock["now"] = datetime(2027, 1, 1, 8, 0, tzinfo=VN)
    new_year = signed(app, "/nodes/cap-so", {"run_id": "r3", "node_id": "cap", "config": {"so": "QD"}})
    assert new_year.data["output"]["so"] == 1
    unknown = signed(app, "/nodes/cap-so", {"run_id": "r4", "node_id": "cap", "config": {"so": "XX"}})
    assert unknown.data["branch"] == "error"


def test_the_dossier_button_numbers_once_writes_the_fields_and_cancelled_numbers_are_kept(make_app, desktiny):
    app = make_app("so-van-ban")
    desktiny.cases["hs-9"] = {"id": "hs-9", "title": "Quyết định nâng lương", "payload": {},
                              "form": {"fields": [{"key": "so_van_ban"}, {"key": "ngay_van_ban"}]}}  # fmt: skip
    issued = call(app, "POST", "/api/ho-so/hs-9/cap-so", {"so": "QD"}, "phien-an")
    assert issued.status == 200 and issued.data["written"] == ["ngay_van_ban", "so_van_ban"]
    assert desktiny.cases["hs-9"]["payload"]["so_van_ban"].startswith("1/QĐ")
    twice = call(app, "POST", "/api/ho-so/hs-9/cap-so", {"so": "QD"}, "phien-an")
    assert twice.data["entry"]["id"] == issued.data["entry"]["id"]
    assert call(app, "POST", f"/api/quan-tri/huy/{issued.data['entry']['id']}", {"ly_do": "Sai"}, "phien-an").status == 403
    call(app, "POST", f"/api/quan-tri/huy/{issued.data['entry']['id']}", {"ly_do": "Ký nhầm"}, "phien-qt")
    desktiny.cases["hs-10"] = {"id": "hs-10", "title": "Khác", "payload": {}, "form": {"fields": []}}
    next_one = call(app, "POST", "/api/ho-so/hs-10/cap-so", {"so": "QD"}, "phien-an").data["entry"]
    assert next_one["number"] == 2  # the cancelled 1 is not reused
    listed = call(app, "GET", "/api/so", session="phien-an").data["entries"]
    assert {e["state"] for e in listed} == {"issued", "cancelled"}
    assert call(app, "GET", "/api/ho-so/khong-co", session="phien-an").status == 404


def test_people_see_only_numbers_of_dossiers_they_may_open_and_managers_see_all(make_app, desktiny):
    app = make_app("so-van-ban")
    for case_id in ("hs-a", "hs-b"):
        desktiny.cases[case_id] = {"id": case_id, "title": f"Hồ sơ {case_id}", "payload": {}, "form": {"fields": []}}
    call(app, "POST", "/api/ho-so/hs-a/cap-so", {"so": "QD"}, "phien-an")
    call(app, "POST", "/api/ho-so/hs-b/cap-so", {"so": "QD"}, "phien-binh")
    del desktiny.cases["hs-a"]  # An's dossier is no longer one Bình (the fake: anyone) may open
    seen = [e["case_id"] for e in call(app, "GET", "/api/so", session="phien-binh").data["entries"]]
    assert seen == ["hs-b"]
    mine = [e["case_id"] for e in call(app, "GET", "/api/so", session="phien-an").data["entries"]]
    assert set(mine) == {"hs-a", "hs-b"}  # An issued hs-a, and may open hs-b
    everything = call(app, "GET", "/api/so", session="phien-qt").data["entries"]
    assert len(everything) == 2
    export = call(app, "GET", "/api/xuat", session="phien-binh").body.decode()
    assert "hs-a" not in export and "Hồ sơ hs-a" not in export
