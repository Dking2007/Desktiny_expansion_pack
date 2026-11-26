# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
from conftest import call, load, signed

luong = load("luong-kpi")
TABLE = luong.brackets(luong.DEFAULTS["bac_thue"])


def test_income_tax_is_progressive():
    assert luong.income_tax(0, TABLE) == 0
    assert luong.income_tax(5_000_000, TABLE) == 250_000
    assert luong.income_tax(10_000_000, TABLE) == 750_000  # 5% of 5M + 10% of 5M
    assert luong.income_tax(100_000_000, TABLE) == 18_150_000 + 7_000_000  # 18,15 triệu tới 80 triệu, 35% phần trên


def test_a_payslip_takes_days_insurance_and_deductions_into_account():
    config = dict(luong.DEFAULTS)
    grade = {"name": "Chuyên viên", "coefficient": 10.0, "allowance": 1_600_000}
    profile = {"extra_allowance": 0, "dependents": 1, "standard_days": 22}
    full = luong.payslip(profile, grade, config, None)
    assert full["gross"] == 25_000_000 and full["insurance"] == 2_625_000
    assert full["taxable"] == 25_000_000 - 2_625_000 - 15_500_000 - 6_200_000
    assert full["net"] == full["gross"] - full["insurance"] - full["tax"]
    half = luong.payslip(profile, grade, config, 11)
    assert half["gross"] == 12_500_000 and half["tax"] == 0


def test_a_payroll_flow_waits_until_the_month_is_locked_and_payslips_stay_private(make_app, desktiny):
    app = make_app("luong-kpi", fetch_attendance=lambda month: {"u-an": 20, "u-binh": 22})
    assert call(app, "POST", "/api/bac-luong", {"code": "CV1", "name": "Chuyên viên", "coefficient": 4}, "phien-qt").status == 200
    grade_id = call(app, "GET", "/api/quan-tri", session="phien-qt").data["grades"][0]["id"]
    saved = call(app, "POST", "/api/ho-so-luong", {"grade_id": grade_id, "people": [
        {"id": "u-an", "display_name": "An"}, {"id": "u-binh", "display_name": "Bình"}]}, "phien-qt")  # fmt: skip
    assert saved.data["saved"] == 2
    step = signed(app, "/nodes/chot-ky-luong", {"call_id": "goi-1", "config": {"ky": "11/2026"}})
    assert step.status == 202
    assert call(app, "GET", "/api/phieu-luong?thang=2026-11", session="phien-an").data["payslip"] is None  # not locked
    overview = call(app, "GET", "/api/quan-tri?thang=2026-11", session="phien-qt").data
    assert overview["period"]["state"] == "computed" and overview["period"]["call_id"] == "goi-1"
    assert call(app, "POST", "/api/chot", {"thang": "2026-11"}, "phien-an").status == 403
    locked = call(app, "POST", "/api/chot", {"thang": "2026-11"}, "phien-qt")
    assert locked.data["state"] == "locked"
    done = [c for c in desktiny.calls if c[0] == "complete_call"][0]
    assert done[2][0:2] == ("goi-1", "success") and done[2][2]["so_nguoi"] == 2
    mine = call(app, "GET", "/api/phieu-luong?thang=2026-11", session="phien-an").data["payslip"]
    assert mine["days"] == 20 and mine["gross"] < 4 * 2_340_000
    tool = signed(app, "/tools/phieu-luong", {"arguments": {"thang": "2026-11"}, "user": {"id": "u-binh"}})
    assert tool.data["result"]["ngay_cong"] == 22
    assert call(app, "POST", "/api/tinh-luong", {"thang": "2026-11"}, "phien-qt").status == 409  # locked stays locked
    bad = signed(app, "/nodes/chot-ky-luong", {"call_id": "goi-2", "config": {"ky": "tháng mười"}})
    assert bad.data["branch"] == "error"


def test_kpi_is_scored_by_someone_else_and_written_into_the_dossier(make_app, desktiny):
    app = make_app("luong-kpi")
    desktiny.cases["hs-1"] = {"id": "hs-1", "title": "Đánh giá KPI quý IV", "owner": {"id": "u-an", "display_name": "An"},
                              "form": {"fields": [{"key": "diem_kpi"}, {"key": "xep_loai"}]}, "payload": {}}  # fmt: skip
    criteria = call(app, "GET", "/api/kpi/hs-1", session="phien-binh").data["criteria"]
    scores = {str(c["id"]): 90 for c in criteria}
    assert call(app, "POST", "/api/kpi/hs-1", {"scores": scores}, "phien-an").status == 403  # one's own
    scored = call(app, "POST", "/api/kpi/hs-1", {"scores": scores}, "phien-binh")
    assert scored.data == {"total": 90.0, "grade": "Hoàn thành xuất sắc", "written": ["diem_kpi", "xep_loai"]}
    assert desktiny.cases["hs-1"]["payload"] == {"diem_kpi": 90.0, "xep_loai": "Hoàn thành xuất sắc"}
    wrong = call(app, "POST", "/api/tieu-chi", {"items": [{"name": "A", "weight": 60}]}, "phien-qt")
    assert wrong.status == 422


def test_grades_and_tax_table_for_the_pages():
    assert [luong.grade_of(t) for t in (95, 90, 80, 50, 49.9)] == [
        "Hoàn thành xuất sắc", "Hoàn thành xuất sắc", "Hoàn thành tốt", "Hoàn thành", "Không hoàn thành"]  # fmt: skip
    assert luong.grade_scale()[0] == {"min": 90, "name": "Hoàn thành xuất sắc"}
    table = luong.tax_table(luong.DEFAULTS["bac_thue"])
    assert table[0] == {"upper": 5_000_000, "rate": 5} and table[-1] == {"upper": None, "rate": 35}
    assert luong.tax_table("không hợp lệ") == []


def test_a_payslip_page_shows_only_ones_own_locked_months(make_app):
    app = make_app("luong-kpi", fetch_attendance=lambda month: {"u-an": 20, "u-binh": 22})
    call(app, "POST", "/api/bac-luong", {"code": "CV1", "name": "Chuyên viên", "coefficient": 4}, "phien-qt")
    grade_id = call(app, "GET", "/api/quan-tri", session="phien-qt").data["grades"][0]["id"]
    call(app, "POST", "/api/ho-so-luong", {"grade_id": grade_id, "people": [
        {"id": "u-an", "display_name": "An"}, {"id": "u-binh", "display_name": "Bình"}]}, "phien-qt")  # fmt: skip
    for month in ("2026-09", "2026-10", "2026-11"):
        assert call(app, "POST", "/api/tinh-luong", {"thang": month}, "phien-qt").status == 200
    for month in ("2026-09", "2026-10"):
        assert call(app, "POST", "/api/chot", {"thang": month}, "phien-qt").status == 200
    page = call(app, "GET", "/api/phieu-luong?thang=2026-11", session="phien-an").data
    assert page["payslip"] is None and page["period_state"] == "computed"  # computed, not locked: nothing shown
    assert [item["month"] for item in page["history"]] == ["2026-09", "2026-10"]
    assert page["history"][0]["days"] == 20 and set(page["history"][0]) == {"month", "gross", "net", "insurance", "tax", "days"}
    assert page["tax_brackets"][-1]["upper"] is None and page["insurance_rate"] == 10.5
    binh = call(app, "GET", "/api/phieu-luong?thang=2026-10", session="phien-binh").data
    assert binh["payslip"]["days"] == 22 and all(item["days"] == 22 for item in binh["history"])
    assert call(app, "GET", "/api/phieu-luong?thang=2026-12", session="phien-an").data["period_state"] is None
    overview = call(app, "GET", "/api/quan-tri?thang=2026-11", session="phien-qt").data
    assert [p["month"] for p in overview["history"]] == ["2026-09", "2026-10", "2026-11"]
    assert overview["history"][-1]["state"] == "computed" and overview["base_salary"] == 2_340_000
    assert overview["kpi"] == {"count": 0, "average": None, "grades": {}}
    assert call(app, "GET", "/api/quan-tri?thang=2026-10", session="phien-an").status == 403


def test_the_kpi_tab_gets_the_grade_scale_and_admin_sees_the_spread(make_app, desktiny):
    app = make_app("luong-kpi")
    desktiny.cases["hs-2"] = {"id": "hs-2", "title": "KPI", "owner": {"id": "u-an", "display_name": "An"},
                              "form": {"fields": []}, "payload": {}}  # fmt: skip
    form = call(app, "GET", "/api/kpi/hs-2", session="phien-binh").data
    assert form["can_score"] is True and [g["min"] for g in form["grade_scale"]] == [90, 75, 50, 0]
    assert call(app, "GET", "/api/kpi/hs-2", session="phien-an").data["can_score"] is False
    scores = {str(c["id"]): 60 for c in form["criteria"]}
    assert call(app, "POST", "/api/kpi/hs-2", {"scores": scores}, "phien-binh").data["written"] == []  # no such fields
    kpi = call(app, "GET", "/api/quan-tri", session="phien-qt").data["kpi"]
    assert kpi == {"count": 1, "average": 60.0, "grades": {"Hoàn thành": 1}}
