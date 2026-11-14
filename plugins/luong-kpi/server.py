# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Lương – KPI: salary grades, monthly payroll with insurance and personal income tax, payslips, KPI scoring.

* Administrators keep grades and people's salary profiles on the plugin's admin page, compute a month (with days
  worked read from the attendance plugin when it is set up) and lock it.
* A flow may hold a payroll dossier at the step "Chốt kỳ lương" (`mode: async`): the plugin computes the month and
  the flow waits until someone locks it on the admin page (or sends it back).
* Each person sees their own payslip once the month is locked; the assistant can read it to them.
* In a KPI dossier, the "Chấm điểm KPI" tab scores weighted criteria and writes the score and grade into the
  dossier's fields (as the person scoring, never the person being scored).

Rates and brackets are settings with defaults for trying the plugin; check them against current regulations.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "lib"))

from mo_rong import App, HttpError, Response, Settings, Store  # noqa: E402
from mo_rong.vn import month_of  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS grades (
  id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL, coefficient REAL NOT NULL,
  allowance REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS profiles (
  user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, grade_id INTEGER REFERENCES grades(id),
  extra_allowance REAL NOT NULL DEFAULT 0, dependents INTEGER NOT NULL DEFAULT 0, standard_days REAL NOT NULL DEFAULT 22
);
CREATE TABLE IF NOT EXISTS periods (
  month TEXT PRIMARY KEY, state TEXT NOT NULL, call_id TEXT, note TEXT, total_net REAL, total_gross REAL,
  people INTEGER, computed_at TEXT, locked_at TEXT, locked_by TEXT
);
CREATE TABLE IF NOT EXISTS payslips (
  month TEXT NOT NULL, user_id TEXT NOT NULL, display_name TEXT NOT NULL, data TEXT NOT NULL, net REAL NOT NULL,
  PRIMARY KEY (month, user_id)
);
CREATE TABLE IF NOT EXISTS criteria (id INTEGER PRIMARY KEY, name TEXT NOT NULL, weight REAL NOT NULL);
CREATE TABLE IF NOT EXISTS kpi (
  case_id TEXT PRIMARY KEY, scores TEXT NOT NULL, total REAL NOT NULL, grade TEXT NOT NULL, scored_by TEXT NOT NULL,
  scored_at TEXT NOT NULL
);
"""
DEFAULTS = {
    "luong_co_so": 2_340_000,
    "ty_le_bao_hiem": 10.5,
    "tran_bao_hiem_lan": 20,
    "giam_tru_ban_than": 15_500_000,
    "giam_tru_phu_thuoc": 6_200_000,
    # Upper bound of each monthly bracket : rate %; the last bracket has no bound.
    "bac_thue": "5000000:5,10000000:10,18000000:15,32000000:20,52000000:25,80000000:30,0:35",
    "url_cham_cong": "",
}
DEFAULT_CRITERIA = [("Khối lượng công việc", 40), ("Chất lượng, tiến độ", 40), ("Tinh thần, kỷ luật", 20)]


def brackets(spec: str) -> list[tuple[float, float]]:
    result = []
    for part in str(spec).split(","):
        bound, _, rate = part.strip().partition(":")
        result.append((float(bound) or float("inf"), float(rate) / 100))
    if not result or result[-1][0] != float("inf"):
        raise ValueError("Bậc thuế cuối cần dạng 0:<thuế suất> (không giới hạn).")
    return result


def income_tax(taxable: float, table: list[tuple[float, float]]) -> float:
    """Progressive tax on monthly taxable income."""
    tax, lower = 0.0, 0.0
    for upper, rate in table:
        if taxable <= lower:
            break
        tax += (min(taxable, upper) - lower) * rate
        lower = upper
    return round(tax)


def payslip(profile: dict, grade: dict, config: dict, days: float | None) -> dict:
    base_salary = float(config["luong_co_so"])
    full = base_salary * grade["coefficient"] + grade["allowance"] + profile["extra_allowance"]
    standard = profile["standard_days"] or 22
    ratio = 1.0 if days is None else max(0.0, min(1.0, days / standard))
    gross = round(full * ratio)
    insured = min(gross, base_salary * float(config["tran_bao_hiem_lan"]))
    insurance = round(insured * float(config["ty_le_bao_hiem"]) / 100)
    deductions = float(config["giam_tru_ban_than"]) + profile["dependents"] * float(config["giam_tru_phu_thuoc"])
    taxable = max(0.0, gross - insurance - deductions)
    tax = income_tax(taxable, brackets(config["bac_thue"]))
    return {
        "grade": grade["name"], "coefficient": grade["coefficient"], "base_salary": base_salary,
        "allowance": grade["allowance"] + profile["extra_allowance"], "days": days, "standard_days": standard,
        "gross": gross, "insurance": insurance, "deductions": deductions, "taxable": round(taxable), "tax": tax,
        "net": gross - insurance - tax,
    }  # fmt: skip


def grade_of(total: float) -> str:
    if total >= 90:
        return "Hoàn thành xuất sắc"
    if total >= 75:
        return "Hoàn thành tốt"
    if total >= 50:
        return "Hoàn thành"
    return "Không hoàn thành"


def build(settings: Settings | None = None, store: Store | None = None, fetch_attendance=None) -> App:
    app = App("luong-kpi", HERE, settings)
    db = store or Store(app.settings.data_dir / "luong-kpi.sqlite3", SCHEMA)
    app.store = db
    if not db.one("SELECT id FROM criteria LIMIT 1"):
        for name, weight in DEFAULT_CRITERIA:
            db.run("INSERT INTO criteria (name, weight) VALUES (?, ?)", name, weight)

    def config() -> dict:
        return app.org_settings(DEFAULTS)

    def attendance(month: str) -> tuple[dict[str, float] | None, str]:
        """Days worked per person from the attendance plugin, or None (whole month counted) and why."""
        if fetch_attendance:
            return fetch_attendance(month), ""
        url, key = str(config().get("url_cham_cong") or ""), str(config().get("khoa_cham_cong") or "")
        if not url or not key:
            return None, "Chưa nối plugin Chấm công: tính đủ công."
        request = urllib.request.Request(url.rstrip("/") + f"/share/cong?thang={month}", headers={"X-Share-Key": key})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (an administrator's URL)
                items = json.loads(response.read())["items"]
        except (urllib.error.URLError, ValueError, KeyError) as exc:
            return None, f"Không đọc được công từ plugin Chấm công ({exc}); tính đủ công."
        return {item["user_id"]: float(item["worked_days"]) for item in items}, ""

    def compute(month: str, call_id: str | None = None) -> dict:
        period = db.one("SELECT * FROM periods WHERE month = ?", month)
        if period and period["state"] == "locked":
            raise HttpError(409, f"Kỳ lương {month} đã chốt.")
        days, note = attendance(month)
        rows = db.all("SELECT p.*, g.name AS grade_name, g.coefficient, g.allowance FROM profiles p "
                      "JOIN grades g ON g.id = p.grade_id ORDER BY p.display_name")  # fmt: skip
        if not rows:
            raise HttpError(409, "Chưa có hồ sơ lương nào (thêm ở trang quản trị).")
        with db.transaction() as tx:
            tx.execute("DELETE FROM payslips WHERE month = ?", (month,))
            totals = {"gross": 0.0, "net": 0.0}
            for row in rows:
                grade = {"name": row["grade_name"], "coefficient": row["coefficient"], "allowance": row["allowance"]}
                slip = payslip(row, grade, config(), None if days is None else days.get(row["user_id"], 0.0))
                totals["gross"] += slip["gross"]
                totals["net"] += slip["net"]
                tx.execute("INSERT INTO payslips (month, user_id, display_name, data, net) VALUES (?, ?, ?, ?, ?)",
                           (month, row["user_id"], row["display_name"], json.dumps(slip, ensure_ascii=False), slip["net"]))  # fmt: skip
            tx.execute(
                "INSERT INTO periods (month, state, call_id, note, total_net, total_gross, people, computed_at) "
                "VALUES (?, 'computed', ?, ?, ?, ?, ?, ?) ON CONFLICT (month) DO UPDATE SET state = 'computed', "
                "call_id = COALESCE(excluded.call_id, periods.call_id), note = excluded.note, total_net = excluded.total_net, "
                "total_gross = excluded.total_gross, people = excluded.people, computed_at = excluded.computed_at",
                (month, call_id, note, totals["net"], totals["gross"], len(rows), datetime.now(timezone.utc).isoformat()),
            )
        return db.one("SELECT * FROM periods WHERE month = ?", month)

    # ---- The payroll flow step (async) --------------------------------------------------------

    @app.route("POST", "/nodes/chot-ky-luong", signed=True)
    def payroll_step(request):
        body = request.json()
        try:
            month = month_of(str((body.get("config") or {}).get("ky") or ""))
        except ValueError:
            return {"branch": "error", "message": "Kỳ lương dạng 2026-11 hoặc 11/2026."}
        try:
            compute(month, body["call_id"])
        except HttpError as exc:
            return {"branch": "error", "message": exc.message}
        return Response(202, json.dumps({"accepted": True}).encode())

    # ---- Administration -------------------------------------------------------------------------

    @app.route("GET", "/api/quan-tri", admin=True)
    def overview(request):
        month = month_of(request.query.get("thang"))
        return {
            "grades": db.all("SELECT * FROM grades ORDER BY coefficient"),
            "profiles": db.all("SELECT * FROM profiles ORDER BY display_name"),
            "period": db.one("SELECT * FROM periods WHERE month = ?", month),
            "payslips": [{**row, "data": json.loads(row["data"])} for row in
                         db.all("SELECT * FROM payslips WHERE month = ? ORDER BY display_name", month)],
            "criteria": db.all("SELECT * FROM criteria ORDER BY id"),
            "month": month,
        }  # fmt: skip

    @app.route("POST", "/api/bac-luong", admin=True)
    def save_grade(request):
        body = request.json()
        code, name = str(body.get("code", "")).strip()[:20], str(body.get("name", "")).strip()[:80]
        try:
            coefficient, allowance = float(body["coefficient"]), float(body.get("allowance") or 0)
        except (KeyError, TypeError, ValueError) as exc:
            raise HttpError(422, "Nhập hệ số lương.") from exc
        if not code or not name or not 0 < coefficient <= 20 or allowance < 0:
            raise HttpError(422, "Cần mã, tên, hệ số trong khoảng 0–20 và phụ cấp không âm.")
        db.run("INSERT INTO grades (code, name, coefficient, allowance) VALUES (?, ?, ?, ?) ON CONFLICT (code) DO UPDATE "
               "SET name = excluded.name, coefficient = excluded.coefficient, allowance = excluded.allowance",
               code, name, coefficient, allowance)  # fmt: skip
        return {"ok": True}

    @app.route("POST", "/api/ho-so-luong", admin=True)
    def save_profile(request):
        body = request.json()
        if not db.one("SELECT id FROM grades WHERE id = ?", int(body.get("grade_id") or 0)):
            raise HttpError(422, "Chọn bậc lương.")
        people = body.get("people") or ([{"id": body["user_id"], "display_name": body.get("display_name", "")}]
                                        if body.get("user_id") else [])  # fmt: skip
        for person in people[:500]:
            db.run("INSERT INTO profiles (user_id, display_name, grade_id, extra_allowance, dependents, standard_days) "
                   "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (user_id) DO UPDATE SET display_name = excluded.display_name, "
                   "grade_id = excluded.grade_id, extra_allowance = excluded.extra_allowance, "
                   "dependents = excluded.dependents, standard_days = excluded.standard_days",
                   str(person["id"]), str(person.get("display_name", ""))[:120], int(body["grade_id"]),
                   max(0.0, float(body.get("extra_allowance") or 0)), max(0, int(body.get("dependents") or 0)),
                   max(1.0, float(body.get("standard_days") or 22)))  # fmt: skip
        return {"saved": len(people[:500])}

    @app.route("GET", "/api/nguoi", admin=True)
    def directory(request):
        """People of Desktiny's directory, to pick whom to give a salary profile."""
        client, cursor, people = app.as_viewer(request), None, []
        while len(people) < 1000:
            page = client.people(department_id=request.query.get("department_id"), cursor=cursor, limit=200)
            people += page["items"]
            cursor = page.get("next_cursor")
            if not cursor:
                break
        return {"items": people}

    @app.route("POST", "/api/tinh-luong", admin=True)
    def compute_now(request):
        return compute(month_of(request.json().get("thang")))

    @app.route("POST", "/api/chot", admin=True)
    def lock(request):
        """Lock the month (payslips become visible); a flow waiting on it carries on."""
        body = request.json()
        month = month_of(body.get("thang"))
        period = db.one("SELECT * FROM periods WHERE month = ?", month)
        if not period or period["state"] != "computed":
            raise HttpError(409, "Tính lương kỳ này trước khi chốt.")
        reject = bool(body.get("tra_lai"))
        state = "draft" if reject else "locked"
        db.run("UPDATE periods SET state = ?, locked_at = ?, locked_by = ?, note = COALESCE(?, note) WHERE month = ?",
               state, datetime.now(timezone.utc).isoformat(), request.viewer["user"]["display_name"],
               body.get("ly_do"), month)  # fmt: skip
        if period["call_id"]:
            if reject:
                app.desktiny.complete_call(period["call_id"], "error", {}, str(body.get("ly_do") or "Bảng lương bị trả lại.")[:300])
            else:
                app.desktiny.complete_call(period["call_id"], "success",
                                           {"tong_thuc_linh": round(period["total_net"]), "tong_quy_luong": round(period["total_gross"]),
                                            "so_nguoi": period["people"]}, f"Đã chốt kỳ lương {month}.")  # fmt: skip
        return {"month": month, "state": state}

    @app.route("POST", "/api/tieu-chi", admin=True)
    def save_criteria(request):
        items = request.json().get("items") or []
        cleaned = [(str(i.get("name", "")).strip()[:80], float(i.get("weight") or 0)) for i in items]
        cleaned = [(name, weight) for name, weight in cleaned if name and weight > 0]
        if not cleaned or abs(sum(w for _, w in cleaned) - 100) > 0.01:
            raise HttpError(422, "Cần ít nhất một tiêu chí; tổng trọng số phải bằng 100.")
        with db.transaction() as tx:
            tx.execute("DELETE FROM criteria")
            tx.executemany("INSERT INTO criteria (name, weight) VALUES (?, ?)", cleaned)
        return {"saved": len(cleaned)}

    # ---- Payslips --------------------------------------------------------------------------------

    def own_slip(user_id: str, month: str) -> dict | None:
        row = db.one("SELECT s.* FROM payslips s JOIN periods p ON p.month = s.month AND p.state = 'locked' "
                     "WHERE s.month = ? AND s.user_id = ?", month, user_id)  # fmt: skip
        return {**json.loads(row["data"]), "month": month} if row else None

    @app.route("GET", "/api/phieu-luong", viewer=True)
    def my_payslip(request):
        month = month_of(request.query.get("thang"))
        return {"user": request.viewer["user"], "month": month, "payslip": own_slip(request.viewer["user"]["id"], month)}

    @app.route("POST", "/tools/phieu-luong", signed=True)
    def tool_payslip(request):
        body = request.json()
        month = month_of((body.get("arguments") or {}).get("thang"))
        slip = own_slip(body["user"]["id"], month)
        if not slip:
            return {"result": {"thang": month, "trang_thai": "Chưa có phiếu lương đã chốt cho tháng này."}}
        return {"result": {"thang": month, "tong_thu_nhap": slip["gross"], "bao_hiem": slip["insurance"],
                           "thue_tncn": slip["tax"], "thuc_linh": slip["net"], "ngay_cong": slip["days"]}}  # fmt: skip

    # ---- KPI scoring (case.tab) -------------------------------------------------------------------

    @app.route("GET", "/api/kpi/{case_id}", viewer=True)
    def kpi_form(request):
        case = app.as_viewer(request).case(request.params["case_id"])
        saved = db.one("SELECT * FROM kpi WHERE case_id = ?", case["id"])
        return {
            "case": {"id": case["id"], "title": case["title"], "owner": case.get("owner")},
            "criteria": db.all("SELECT * FROM criteria ORDER BY id"),
            "saved": {**saved, "scores": json.loads(saved["scores"])} if saved else None,
            "can_score": (case.get("owner") or {}).get("id") != request.viewer["user"]["id"],
        }

    @app.route("POST", "/api/kpi/{case_id}", viewer=True)
    def kpi_score(request):
        client = app.as_viewer(request)
        case = client.case(request.params["case_id"])
        if (case.get("owner") or {}).get("id") == request.viewer["user"]["id"]:
            raise HttpError(403, "Người được đánh giá không tự chấm điểm cuối cùng.")
        criteria = db.all("SELECT * FROM criteria ORDER BY id")
        scores = request.json().get("scores") or {}
        total = 0.0
        for item in criteria:
            value = scores.get(str(item["id"]))
            if not isinstance(value, int | float) or not 0 <= value <= 100:
                raise HttpError(422, f"Chấm “{item['name']}” từ 0 đến 100.")
            total += value * item["weight"] / 100
        total = round(total, 1)
        grade = grade_of(total)
        fields = {key["key"] for key in (case.get("form") or {}).get("fields", [])}
        values = {k: v for k, v in {"diem_kpi": total, "xep_loai": grade}.items() if k in fields}
        if values:
            client.write_fields(case["id"], values, key=f"kpi:{case['id']}:{total}:{grade}")
        db.run("INSERT INTO kpi (case_id, scores, total, grade, scored_by, scored_at) VALUES (?, ?, ?, ?, ?, ?) "
               "ON CONFLICT (case_id) DO UPDATE SET scores = excluded.scores, total = excluded.total, grade = excluded.grade, "
               "scored_by = excluded.scored_by, scored_at = excluded.scored_at",
               case["id"], json.dumps(scores), total, grade, request.viewer["user"]["display_name"],
               datetime.now(timezone.utc).isoformat())  # fmt: skip
        return {"total": total, "grade": grade, "written": sorted(values)}

    @app.route("POST", "/events", signed=True)
    def events(request):
        if request.json().get("type") == "plugin.settings.changed":
            app.forget_settings()
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9202)
