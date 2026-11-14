# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Chấm công: check in and out by GPS at the office, shifts and lateness, monthly attendance.

The plugin keeps its own records (SQLite). Desktiny shows its pages, knows who is checking in (the frame's
session), receives an event when someone is late too often, and lets the assistant answer "how many times was I
late this month". Other plugins (payroll) may read a month's attendance with a shared key.
"""

from __future__ import annotations

import csv
import hmac
import io
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "lib"))

from mo_rong import App, HttpError, Response, Settings, Store  # noqa: E402
from mo_rong.vn import month_of  # noqa: E402

VN = timezone(timedelta(hours=7))
SCHEMA = """
CREATE TABLE IF NOT EXISTS shifts (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
  grace_minutes INTEGER NOT NULL DEFAULT 5, standard_hours REAL NOT NULL DEFAULT 8
);
CREATE TABLE IF NOT EXISTS places (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL, radius_m INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS assignments (
  user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, shift_id INTEGER REFERENCES shifts(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS punches (
  id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, display_name TEXT NOT NULL, day TEXT NOT NULL, kind TEXT NOT NULL,
  at TEXT NOT NULL, lat REAL, lng REAL, accuracy REAL, place_id INTEGER, late_minutes INTEGER NOT NULL DEFAULT 0,
  UNIQUE (user_id, day, kind)
);
CREATE TABLE IF NOT EXISTS announced (key TEXT PRIMARY KEY);
"""
DEFAULTS = {"nguong_di_muon": 3, "do_chinh_xac_toi_da": 100}


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres (haversine)."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def minutes(clock: str) -> int:
    hours, mins = clock.split(":")
    return int(hours) * 60 + int(mins)


def build(settings: Settings | None = None, store: Store | None = None, now=lambda: datetime.now(VN)) -> App:
    app = App("cham-cong", HERE, settings)
    db = store or Store(app.settings.data_dir / "cham-cong.sqlite3", SCHEMA)
    app.store = db

    def config() -> dict:
        return app.org_settings(DEFAULTS)

    def shift_of(user_id: str) -> dict | None:
        return db.one(
            "SELECT s.* FROM assignments a JOIN shifts s ON s.id = a.shift_id WHERE a.user_id = ?", user_id
        ) or db.one("SELECT * FROM shifts ORDER BY id LIMIT 1")

    def month_rows(month: str, user_id: str | None = None) -> list[dict]:
        sql = "SELECT * FROM punches WHERE day LIKE ?" + (" AND user_id = ?" if user_id else "") + " ORDER BY day, kind"
        return db.all(sql, f"{month}-%", *([user_id] if user_id else []))

    def summary(month: str, user_id: str | None = None) -> list[dict]:
        """Per person: days present, late check-ins and minutes, early leaves, hours worked."""
        people: dict[str, dict] = {}
        for row in month_rows(month, user_id):
            person = people.setdefault(row["user_id"], {
                "user_id": row["user_id"], "display_name": row["display_name"], "days": {}, "late_count": 0,
                "late_minutes": 0, "early_count": 0})  # fmt: skip
            day = person["days"].setdefault(row["day"], {})
            day[row["kind"]] = row["at"]
            if row["kind"] == "in" and row["late_minutes"] > 0:
                person["late_count"] += 1
                person["late_minutes"] += row["late_minutes"]
            if row["kind"] == "out" and row["late_minutes"] < 0:
                person["early_count"] += 1
        result = []
        for person in people.values():
            hours = 0.0
            for times in person["days"].values():
                if "in" in times and "out" in times:
                    start, end = datetime.fromisoformat(times["in"]), datetime.fromisoformat(times["out"])
                    hours += max(0.0, (end - start).total_seconds() / 3600)
            person["worked_days"] = len(person["days"])
            person["hours"] = round(hours, 2)
            result.append(person)
        return sorted(result, key=lambda p: p["display_name"])

    # ---- Checking in (the person's own page) ---------------------------------------------------

    @app.route("GET", "/api/toi", viewer=True)
    def mine(request):
        user = request.viewer["user"]
        today = now().date().isoformat()
        punches = {row["kind"]: row for row in db.all("SELECT * FROM punches WHERE user_id = ? AND day = ?", user["id"], today)}
        month = month_of(request.query.get("thang"))
        mine_summary = next(iter(summary(month, user["id"])), {"worked_days": 0, "late_count": 0, "hours": 0})
        return {
            "user": user,
            "today": today,
            "shift": shift_of(user["id"]),
            "places": db.all("SELECT id, name, radius_m FROM places ORDER BY name"),
            "punches": punches,
            "month": month,
            "summary": {k: mine_summary.get(k) for k in ("worked_days", "late_count", "late_minutes", "early_count", "hours")},
            "history": month_rows(month, user["id"]),
        }

    @app.route("POST", "/api/cham", viewer=True)
    def punch(request):
        user = request.viewer["user"]
        body = request.json()
        kind = body.get("kind")
        if kind not in {"in", "out"}:
            raise HttpError(422, "Chọn vào ca hoặc ra ca.")
        try:
            lat, lng, accuracy = float(body["lat"]), float(body["lng"]), float(body.get("accuracy") or 0)
        except (KeyError, TypeError, ValueError) as exc:
            raise HttpError(422, "Thiếu vị trí GPS. Cho phép trình duyệt dùng vị trí rồi thử lại.") from exc
        if accuracy > float(config()["do_chinh_xac_toi_da"]):
            raise HttpError(422, f"Vị trí chưa đủ chính xác (±{round(accuracy)} m). Ra chỗ thoáng rồi thử lại.")
        places = db.all("SELECT * FROM places")
        if not places:
            raise HttpError(409, "Quản trị chưa khai địa điểm chấm công.")
        nearest = min(places, key=lambda p: distance_m(lat, lng, p["lat"], p["lng"]))
        far = distance_m(lat, lng, nearest["lat"], nearest["lng"])
        if far > nearest["radius_m"]:
            raise HttpError(422, f"Bạn đang cách “{nearest['name']}” khoảng {round(far)} m, ngoài phạm vi {nearest['radius_m']} m.")
        moment = now()
        today = moment.date().isoformat()
        if kind == "out" and not db.one("SELECT id FROM punches WHERE user_id = ? AND day = ? AND kind = 'in'", user["id"], today):
            raise HttpError(409, "Chưa chấm vào ca hôm nay.")
        shift = shift_of(user["id"])
        late = 0
        if shift:
            clock = moment.hour * 60 + moment.minute
            if kind == "in":
                late = max(0, clock - minutes(shift["start"]) - int(shift["grace_minutes"]))
            else:
                late = min(0, clock - minutes(shift["end"]))  # negative: left early
        with db.transaction() as tx:
            if tx.execute("SELECT id FROM punches WHERE user_id = ? AND day = ? AND kind = ?", (user["id"], today, kind)).fetchone():
                raise HttpError(409, "Hôm nay bạn đã chấm " + ("vào ca." if kind == "in" else "ra ca."))
            tx.execute(
                "INSERT INTO punches (user_id, display_name, day, kind, at, lat, lng, accuracy, place_id, late_minutes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], user["display_name"], today, kind, moment.isoformat(timespec="seconds"), lat, lng,
                 accuracy, nearest["id"], late),
            )  # fmt: skip
        if kind == "in" and late > 0:
            announce_lateness(user, moment.strftime("%Y-%m"))
        return {"ok": True, "kind": kind, "at": moment.isoformat(timespec="seconds"), "late_minutes": late,
                "place": nearest["name"]}  # fmt: skip

    def announce_lateness(user: dict, month: str):
        """Once a person reaches the threshold in a month, Desktiny gets `di_muon` (flows may start on it)."""
        count = next(iter(summary(month, user["id"])), {}).get("late_count", 0)
        threshold = int(config()["nguong_di_muon"])
        key = f"di_muon:{user['id']}:{month}:{count}"
        if count < threshold or db.one("SELECT key FROM announced WHERE key = ?", key):
            return
        db.run("INSERT INTO announced (key) VALUES (?)", key)
        if app.settings.token:
            app.desktiny.send_event("di_muon", {"nhan_vien": user["id"], "so_lan": count, "thang": month}, key=key)

    # ---- Administration (admin.page) -------------------------------------------------------------

    @app.route("GET", "/api/quan-tri", admin=True)
    def overview(request):
        month = month_of(request.query.get("thang"))
        return {
            "shifts": db.all("SELECT * FROM shifts ORDER BY start"),
            "places": db.all("SELECT * FROM places ORDER BY name"),
            "assignments": db.all("SELECT * FROM assignments ORDER BY display_name"),
            "month": month,
            "summary": [{k: v for k, v in p.items() if k != "days"} for p in summary(month)],
            "settings": config(),
        }

    @app.route("POST", "/api/ca", admin=True)
    def save_shift(request):
        body = request.json()
        name = str(body.get("name", "")).strip()[:60]
        start, end = str(body.get("start", "")), str(body.get("end", ""))
        for clock in (start, end):
            try:
                if not 0 <= minutes(clock) < 24 * 60:
                    raise ValueError
            except ValueError as exc:
                raise HttpError(422, "Giờ dạng HH:MM.") from exc
        if not name:
            raise HttpError(422, "Đặt tên ca.")
        grace = max(0, min(120, int(body.get("grace_minutes") or 0)))
        hours = max(1.0, min(24.0, float(body.get("standard_hours") or 8)))
        if body.get("id"):
            db.run("UPDATE shifts SET name = ?, start = ?, end = ?, grace_minutes = ?, standard_hours = ? WHERE id = ?",
                   name, start, end, grace, hours, int(body["id"]))  # fmt: skip
            return {"id": int(body["id"])}
        return {"id": db.run("INSERT INTO shifts (name, start, end, grace_minutes, standard_hours) VALUES (?, ?, ?, ?, ?)",
                             name, start, end, grace, hours)}  # fmt: skip

    @app.route("DELETE", "/api/ca/{shift_id}", admin=True)
    def delete_shift(request):
        db.run("DELETE FROM shifts WHERE id = ?", int(request.params["shift_id"]))
        return {"ok": True}

    @app.route("POST", "/api/dia-diem", admin=True)
    def save_place(request):
        body = request.json()
        try:
            lat, lng, radius = float(body["lat"]), float(body["lng"]), int(body.get("radius_m") or 100)
        except (KeyError, TypeError, ValueError) as exc:
            raise HttpError(422, "Nhập vĩ độ, kinh độ và bán kính.") from exc
        if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 20 <= radius <= 5000):
            raise HttpError(422, "Toạ độ không hợp lệ hoặc bán kính ngoài 20–5000 m.")
        name = str(body.get("name", "")).strip()[:80] or "Trụ sở"
        return {"id": db.run("INSERT INTO places (name, lat, lng, radius_m) VALUES (?, ?, ?, ?)", name, lat, lng, radius)}

    @app.route("DELETE", "/api/dia-diem/{place_id}", admin=True)
    def delete_place(request):
        db.run("DELETE FROM places WHERE id = ?", int(request.params["place_id"]))
        return {"ok": True}

    @app.route("POST", "/api/phan-ca", admin=True)
    def assign(request):
        """Give people a shift; the people come from Desktiny's directory (people.list) by unit."""
        body = request.json()
        shift_id = int(body["shift_id"]) if body.get("shift_id") else None
        people = body.get("people") or []
        if body.get("department_id"):
            cursor, people = None, []
            while True:
                page = app.as_viewer(request).people(department_id=body["department_id"], cursor=cursor, limit=200)
                people += page["items"]
                cursor = page.get("next_cursor")
                if not cursor:
                    break
        for person in people[:500]:
            db.run("INSERT INTO assignments (user_id, display_name, shift_id) VALUES (?, ?, ?) "
                   "ON CONFLICT (user_id) DO UPDATE SET display_name = excluded.display_name, shift_id = excluded.shift_id",
                   str(person["id"]), str(person.get("display_name", ""))[:120], shift_id)  # fmt: skip
        return {"assigned": min(len(people), 500)}

    @app.route("GET", "/api/xuat", admin=True)
    def export(request):
        month = month_of(request.query.get("thang"))
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Mã người dùng", "Họ tên", "Số ngày có mặt", "Số lần đi muộn", "Phút đi muộn", "Về sớm", "Số giờ"])
        for person in summary(month):
            writer.writerow([person["user_id"], person["display_name"], person["worked_days"], person["late_count"],
                             person["late_minutes"], person["early_count"], person["hours"]])  # fmt: skip
        return Response(200, ("﻿" + out.getvalue()).encode(), "text/csv; charset=utf-8",
                        {"Content-Disposition": f'attachment; filename="cham-cong-{month}.csv"'})  # fmt: skip

    # ---- From Desktiny and other plugins --------------------------------------------------------

    @app.route("POST", "/events", signed=True)
    def events(request):
        if request.json().get("type") == "plugin.settings.changed":
            app.forget_settings()
        return Response(202, b"{}")

    @app.route("POST", "/tools/di-muon", signed=True)
    def tool_late(request):
        body = request.json()
        month = month_of((body.get("arguments") or {}).get("thang"))
        mine_summary = next(iter(summary(month, body["user"]["id"])), {})
        return {"result": {"thang": month, "so_lan_di_muon": mine_summary.get("late_count", 0),
                           "so_phut_di_muon": mine_summary.get("late_minutes", 0)}}  # fmt: skip

    @app.route("POST", "/tools/cong-thang", signed=True)
    def tool_month(request):
        body = request.json()
        month = month_of((body.get("arguments") or {}).get("thang"))
        mine_summary = next(iter(summary(month, body["user"]["id"])), {})
        return {"result": {"thang": month, "so_ngay_co_mat": mine_summary.get("worked_days", 0),
                           "so_gio": mine_summary.get("hours", 0), "ve_som": mine_summary.get("early_count", 0)}}  # fmt: skip

    @app.route("GET", "/share/cong")
    def shared_month(request):
        """A month's attendance for the payroll plugin, with the key both plugins were given."""
        key = str(config().get("khoa_chia_se") or "")
        if not key or not hmac.compare_digest(key, request.header("x-share-key")):
            raise HttpError(401, "Sai khoá chia sẻ.", "share_key_invalid")
        month = month_of(request.query.get("thang"))
        return {"month": month, "items": [{k: v for k, v in p.items() if k != "days"} for p in summary(month)]}

    return app


if __name__ == "__main__":
    build().run(9201)
