# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Sổ văn bản đến: the register of incoming documents, one gapless series of "số đến" per year.

Each incoming document is a dossier (process "Xử lý văn bản đến"); registering it reads the sender, the original
number, the summary, the urgency and the deadline from the dossier's form, hands out the next số đến once (asking
again for the same dossier gives the same number) and writes số đến and ngày đến back into the form. Registering
happens from the dossier's button (which writes the fields, as the person) or from a flow step (which hands them
on as outputs: Desktiny lets a plugin write form fields only in a person's session, so the flow writes them with
its own "Cập nhật hồ sơ" step). When the dossier closes, the entry is marked done; the
register shows what is still being handled, what is due soon and what is overdue.
"""

from __future__ import annotations

import csv
import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "lib"))

from desktiny_plugin import PluginError  # noqa: E402
from mo_rong import App, HttpError, Response, Settings, Store  # noqa: E402
from mo_rong.vn import csv_cells, parse_date  # noqa: E402

VN = timezone(timedelta(hours=7))
SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY, year INTEGER NOT NULL, number INTEGER NOT NULL, case_id TEXT UNIQUE,
  sender TEXT NOT NULL, original_number TEXT NOT NULL, document_date TEXT, kind TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL, urgency TEXT NOT NULL DEFAULT 'Thường', due TEXT, received_at TEXT NOT NULL,
  registered_by TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'open', outcome TEXT, closed_at TEXT,
  cancel_reason TEXT, UNIQUE (year, number)
);
"""
URGENT = {"Khẩn", "Thượng khẩn", "Hoả tốc", "Hỏa tốc"}
DEFAULTS = {"bao_truoc_ngay": 2}
STATES = {"open": "Đang xử lý", "done": "Đã xử lý", "cancelled": "Đã huỷ số"}


def build(settings: Settings | None = None, store: Store | None = None, now=lambda: datetime.now(VN)) -> App:
    app = App("so-van-ban-den", HERE, settings)
    db = store or Store(app.settings.data_dir / "so-van-ban-den.sqlite3", SCHEMA)
    app.store = db

    def soon_days() -> int:
        try:
            return max(0, min(30, int(app.org_settings(DEFAULTS)["bao_truoc_ngay"])))
        except (TypeError, ValueError):
            return DEFAULTS["bao_truoc_ngay"]

    def shown(entry: dict) -> dict:
        """An entry with how it stands today: đang xử lý, sắp đến hạn, quá hạn, đã xử lý."""
        today = now().date()
        due = parse_date(entry["due"])
        left = (due - today).days if due else None
        if entry["state"] != "open":
            status = entry["state"]
        elif left is not None and left < 0:
            status = "overdue"
        elif left is not None and left <= soon_days():
            status = "due_soon"
        else:
            status = "open"
        return {**entry, "status": status, "left": left, "urgent": entry["urgency"] in URGENT}

    def fields_of(case: dict) -> set[str]:
        return {f["key"] for f in (case.get("form") or {}).get("fields", [])}

    def register(client, case: dict, by: str, write: bool = True) -> tuple[dict, list[str]]:
        """Give the dossier its số đến (once) and, with `write`, put it into the form; returns (entry, fields written)."""
        payload = case.get("payload") or {}
        sender = str(payload.get("noi_gui") or "").strip()
        summary = str(payload.get("trich_yeu") or case.get("title") or "").strip()
        if not sender or not summary:
            raise HttpError(422, "Văn bản cần có “Cơ quan, tổ chức gửi” và “Trích yếu nội dung” trước khi vào sổ.")
        moment = now()
        due = parse_date(payload.get("han_xu_ly")) or parse_date(case.get("due_at"))
        written_on = parse_date(payload.get("ngay_van_ban"))
        with db.transaction() as tx:
            found = tx.execute("SELECT * FROM entries WHERE case_id = ?", (case["id"],)).fetchone()
            if not found:
                last = tx.execute("SELECT MAX(number) FROM entries WHERE year = ?", (moment.year,)).fetchone()[0]
                tx.execute(
                    "INSERT INTO entries (year, number, case_id, sender, original_number, document_date, kind, summary, "
                    "urgency, due, received_at, registered_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (moment.year, (last or 0) + 1, case["id"], sender[:300],
                     str(payload.get("so_ky_hieu_goc") or "").strip()[:100],
                     written_on.isoformat() if written_on else None,
                     str(payload.get("loai_van_ban") or "").strip()[:60], summary[:1000],
                     str(payload.get("do_khan") or "Thường").strip()[:30], due.isoformat() if due else None,
                     moment.isoformat(timespec="seconds"), by[:120]),
                )  # fmt: skip
            entry = dict(tx.execute("SELECT * FROM entries WHERE case_id = ?", (case["id"],)).fetchone())
        values = {k: v for k, v in {"so_den": str(entry["number"]), "ngay_den": entry["received_at"][:10]}.items()
                  if write and k in fields_of(case) and payload.get(k) != v}  # fmt: skip
        if values:
            client.write_fields(case["id"], values, key=f"so-van-ban-den:{entry['id']}")
        return entry, sorted(values)

    def visible(request, rows: list[dict]) -> list[dict]:
        """The whole register for the admin page; for others, documents they may open or registered themselves."""
        if (request.viewer.get("context") or {}).get("slot") == "admin.page":
            return rows
        client, name, seen = app.as_viewer(request), request.viewer["user"]["display_name"], {}

        def may_open(case_id: str) -> bool:
            if case_id not in seen:
                try:
                    client.case(case_id)
                    seen[case_id] = True
                except PluginError:
                    seen[case_id] = False
            return seen[case_id]

        return [row for row in rows if row["registered_by"] == name or (row["case_id"] and may_open(row["case_id"]))]

    def listing(request) -> list[dict]:
        year = int(request.query.get("nam") or now().year)
        sql, args = "SELECT * FROM entries WHERE year = ?", [year]
        if request.query.get("q"):
            like = f"%{request.query['q']}%"
            sql, args = sql + " AND (summary LIKE ? OR sender LIKE ? OR original_number LIKE ?)", [*args, like, like, like]
        rows = [shown(row) for row in visible(request, db.all(sql + " ORDER BY number DESC LIMIT 2000", *args))]
        wanted = request.query.get("tinh_trang")
        return [row for row in rows if not wanted or row["status"] == wanted]

    def counts(rows: list[dict]) -> dict:
        return {key: sum(1 for row in rows if row["status"] == key) for key in ("open", "due_soon", "overdue", "done")}

    def next_number(year: int) -> int:
        """The số đến the next document registered this year would get (cancelled numbers are never reused)."""
        return (db.one("SELECT MAX(number) AS last FROM entries WHERE year = ?", year)["last"] or 0) + 1

    def years() -> list[int]:
        """The years the register has entries for, and this year, newest first."""
        found = {row["year"] for row in db.all("SELECT DISTINCT year FROM entries")}
        return sorted(found | {now().year}, reverse=True)

    def deadline(due) -> dict | None:
        """How a deadline stands today: the date, days left and whether it is due soon or overdue."""
        day = parse_date(due)
        if not day:
            return None
        left = (day - now().date()).days
        return {"due": day.isoformat(), "left": left, "status": "overdue" if left < 0 else "due_soon" if left <= soon_days() else "open"}

    # ---- Flow step ------------------------------------------------------------------------------

    @app.route("POST", "/nodes/vao-so", signed=True)
    def step(request):
        subject = request.json().get("subject") or {}
        if subject.get("type") != "case":
            return {"branch": "error", "message": "Bước này chỉ dùng trong quy trình văn bản (hồ sơ)."}
        try:
            case = app.desktiny.case(subject["id"])
            entry, _ = register(app.desktiny, case, "Quy trình", write=False)
        except (HttpError, PluginError) as exc:
            return {"branch": "error", "message": getattr(exc, "message", str(exc))}
        return {"branch": "success", "output": {"so_den": str(entry["number"]), "ngay_den": entry["received_at"][:10],
                                                "han_xu_ly": entry["due"] or ""}}  # fmt: skip

    # ---- Dossier: side panel and action ---------------------------------------------------------

    @app.route("GET", "/api/van-ban/{case_id}", viewer=True)
    def of_case(request):
        case = app.as_viewer(request).case(request.params["case_id"])
        entry = db.one("SELECT * FROM entries WHERE case_id = ?", case["id"])
        payload = case.get("payload") or {}
        draft = {"noi_gui": payload.get("noi_gui") or "", "so_ky_hieu_goc": payload.get("so_ky_hieu_goc") or "",
                 "trich_yeu": payload.get("trich_yeu") or case.get("title") or "", "do_khan": payload.get("do_khan") or "Thường",
                 "han_xu_ly": payload.get("han_xu_ly") or "", "ngay_van_ban": payload.get("ngay_van_ban") or "",
                 "loai_van_ban": payload.get("loai_van_ban") or "", "nguoi_xu_ly": payload.get("nguoi_xu_ly") or ""}  # fmt: skip
        # The deadline as the dossier has it now: the leader often sets “Hạn xử lý” after the document is registered.
        due = payload.get("han_xu_ly") or (entry or {}).get("due") or case.get("due_at")
        return {"case": {"id": case["id"], "title": case["title"]}, "entry": shown(entry) if entry else None, "draft": draft,
                "today": now().date().isoformat(), "next_number": None if entry else next_number(now().year),
                "deadline": deadline(due) if not entry or entry["state"] == "open" else None,
                "bao_truoc_ngay": soon_days()}  # fmt: skip

    @app.route("POST", "/api/van-ban/{case_id}/vao-so", viewer=True)
    def register_case(request):
        client = app.as_viewer(request)
        case = client.case(request.params["case_id"])  # the viewer must be able to see the document
        entry, written = register(client, case, request.viewer["user"]["display_name"])
        return {"entry": shown(entry), "written": written}

    # ---- Register -------------------------------------------------------------------------------

    @app.route("GET", "/api/so", viewer=True)
    def register_page(request):
        rows = listing(request)
        return {"entries": rows, "counts": counts(rows), "states": STATES, "years": years(), "bao_truoc_ngay": soon_days()}

    @app.route("GET", "/api/can-xu-ly", viewer=True)
    def to_handle(request):
        """Home block: open documents the viewer may see, the most pressing first."""
        rows = [shown(row) for row in visible(request, db.all("SELECT * FROM entries WHERE state = 'open' ORDER BY number DESC LIMIT 500"))]
        rows.sort(key=lambda r: (r["status"] != "overdue", not r["urgent"], r["left"] if r["left"] is not None else 9999))
        return {"items": rows[:10], "counts": counts(rows), "bao_truoc_ngay": soon_days()}

    @app.route("GET", "/api/xuat", viewer=True)
    def export(request):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Số đến", "Ngày đến", "Cơ quan gửi", "Số, ký hiệu", "Ngày văn bản", "Trích yếu", "Mức độ khẩn",
                         "Hạn xử lý", "Tình trạng"])  # fmt: skip
        labels = {**STATES, "overdue": "Quá hạn", "due_soon": "Sắp đến hạn"}
        for row in listing(request):
            writer.writerow(csv_cells([row["number"], row["received_at"][:10], row["sender"], row["original_number"],
                                       row["document_date"] or "", row["summary"], row["urgency"], row["due"] or "",
                                       labels.get(row["status"], row["status"])]))  # fmt: skip
        return Response(200, ("﻿" + out.getvalue()).encode(), "text/csv; charset=utf-8")

    @app.route("GET", "/api/quan-tri/tong-quan", admin=True)
    def overview(request):
        """The register's settings and where it stands, for the admin page: the next số đến and the year by month."""
        year = now().year
        months = [0] * 12
        for row in db.all("SELECT received_at FROM entries WHERE year = ? AND state != 'cancelled'", year):
            months[int(row["received_at"][5:7]) - 1] += 1
        cancelled = db.one("SELECT COUNT(*) AS n FROM entries WHERE year = ? AND state = 'cancelled'", year)["n"]
        return {"year": year, "today": now().date().isoformat(), "next_number": next_number(year), "bao_truoc_ngay": soon_days(),
                "months": months, "cancelled": cancelled, "years": years()}  # fmt: skip

    @app.route("POST", "/api/quan-tri/huy/{entry_id}", admin=True)
    def cancel(request):
        """Mark a number cancelled: it stays in the register and is never handed out again."""
        reason = str(request.json().get("ly_do", "")).strip()[:300]
        if not reason:
            raise HttpError(422, "Nêu lý do huỷ số đến.")
        db.run("UPDATE entries SET state = 'cancelled', cancel_reason = ?, closed_at = ? WHERE id = ?",
               reason, now().isoformat(timespec="seconds"), int(request.params["entry_id"]))  # fmt: skip
        return {"ok": True}

    # ---- Assistant and events -------------------------------------------------------------------

    @app.route("POST", "/tools/van-ban-den", signed=True)
    def tool(request):
        body = request.json()
        wanted = str((body.get("arguments") or {}).get("tinh_trang") or "").strip()
        client = app.client_factory(body.get("token") or "")
        rows, result = db.all("SELECT * FROM entries WHERE state = 'open' ORDER BY number DESC LIMIT 300"), []
        for row in map(shown, rows):
            if wanted in ("qua_han", "quá hạn") and row["status"] != "overdue":
                continue
            try:
                client.case(row["case_id"])
            except PluginError:
                continue
            result.append({"so_den": row["number"], "noi_gui": row["sender"], "trich_yeu": row["summary"],
                           "han_xu_ly": row["due"], "qua_han": row["status"] == "overdue", "khan": row["urgency"]})  # fmt: skip
            if len(result) >= 20:
                break
        return {"result": result}

    @app.route("POST", "/events", signed=True)
    def events(request):
        body = request.json()
        kind, subject = body.get("type"), body.get("subject") or {}
        if kind == "plugin.settings.changed":
            app.forget_settings()
        elif kind == "case.closed" and subject.get("type") == "case":
            try:
                outcome = app.desktiny.case(subject["id"]).get("status", "")
            except PluginError:
                outcome = ""
            db.run("UPDATE entries SET state = 'done', outcome = ?, closed_at = ? WHERE case_id = ? AND state = 'open'",
                   outcome, now().isoformat(timespec="seconds"), subject.get("id"))  # fmt: skip
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9207)
