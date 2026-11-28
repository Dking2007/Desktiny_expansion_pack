# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Sổ văn bản: registers of outgoing documents numbered without gaps, one series per register and year.

A number is handed out once and never again: asking twice with the same key (the same flow step, the same
dossier) gives the same number back; a number that should not have been issued is marked cancelled, not reused.
Numbers come from a flow step ("Cấp số văn bản") or from the dossier's action button, which also writes the
number and date into the dossier's form when it has those fields.
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
from mo_rong import App, HttpError, Response, Settings, Store, require_listed  # noqa: E402
from mo_rong.vn import csv_cells  # noqa: E402

VN = timezone(timedelta(hours=7))
SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, symbol TEXT NOT NULL, start_number INTEGER NOT NULL DEFAULT 1,
  yearly INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY, book TEXT NOT NULL REFERENCES books(code), year INTEGER NOT NULL, number INTEGER NOT NULL,
  full_number TEXT NOT NULL, case_id TEXT, summary TEXT NOT NULL DEFAULT '', issued_at TEXT NOT NULL,
  issued_by TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'issued', cancel_reason TEXT, key TEXT UNIQUE,
  UNIQUE (book, year, number)
);
"""
DEFAULT_BOOKS = [("QD", "Quyết định", "QĐ"), ("CV", "Công văn", ""), ("TB", "Thông báo", "TB"), ("GXN", "Giấy xác nhận", "GXN")]
DEFAULTS = {"ky_hieu_co_quan": "UBND", "ten_co_quan": "", "dia_danh": ""}


def build(settings: Settings | None = None, store: Store | None = None, now=lambda: datetime.now(VN)) -> App:
    app = App("so-van-ban", HERE, settings)
    db = store or Store(app.settings.data_dir / "so-van-ban.sqlite3", SCHEMA)
    app.store = db
    if not db.one("SELECT code FROM books LIMIT 1"):
        for code, name, symbol in DEFAULT_BOOKS:
            db.run("INSERT INTO books (code, name, symbol) VALUES (?, ?, ?)", code, name, symbol)

    def full_number(number: int, book: dict) -> str:
        agency = str(app.org_settings(DEFAULTS)["ky_hieu_co_quan"]).strip()
        # "12/QĐ-UBND"; a register without its own symbol (công văn) is "12/UBND".
        tail = "-".join(part for part in (book["symbol"], agency) if part)
        return f"{number}/{tail}" if tail else str(number)

    def issue(book_code: str, *, key: str, case_id: str | None, summary: str, by: str) -> dict:
        """The next number of the register's current series, once per key."""
        book = db.one("SELECT * FROM books WHERE code = ?", book_code)
        if not book:
            raise HttpError(422, f"Không có sổ “{book_code}”.")
        moment = now()
        with db.transaction() as tx:
            found = tx.execute("SELECT * FROM entries WHERE key = ?", (key,)).fetchone()
            if found:
                return dict(found)
            year = moment.year if book["yearly"] else 0
            last = tx.execute("SELECT MAX(number) FROM entries WHERE book = ? AND year = ?", (book_code, year)).fetchone()[0]
            number = (last or book["start_number"] - 1) + 1
            tx.execute(
                "INSERT INTO entries (book, year, number, full_number, case_id, summary, issued_at, issued_by, key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (book_code, year, number, full_number(number, book), case_id, summary[:500],
                 moment.isoformat(timespec="seconds"), by[:120], key),
            )  # fmt: skip
            return dict(tx.execute("SELECT * FROM entries WHERE key = ?", (key,)).fetchone())

    def books(with_next: bool = False):
        rows = db.all("SELECT * FROM books ORDER BY name")
        if not with_next:
            return rows
        # What the next number of each register's current series will be (a preview: the number itself is only
        # taken when it is issued), and how many numbers that series holds.
        year = now().year
        for book in rows:
            series = year if book["yearly"] else 0
            last = db.one("SELECT MAX(number) AS last, COUNT(*) AS total, SUM(state = 'cancelled') AS cancelled "
                          "FROM entries WHERE book = ? AND year = ?", book["code"], series)  # fmt: skip
            book["next_number"] = (last["last"] or book["start_number"] - 1) + 1
            book["next_full_number"] = full_number(book["next_number"], book)
            book["issued"], book["cancelled"] = last["total"] or 0, last["cancelled"] or 0
        return rows

    def agency() -> dict:
        """The issuing agency as the document heading shows it (read only; set in the plugin's settings)."""
        values = app.org_settings(DEFAULTS)
        return {"symbol": str(values.get("ky_hieu_co_quan") or "").strip(), "name": str(values.get("ten_co_quan") or "").strip(),
                "place": str(values.get("dia_danh") or "").strip()}  # fmt: skip

    # ---- Flow step ------------------------------------------------------------------------------

    @app.route("POST", "/nodes/cap-so", signed=True)
    def step(request):
        body = request.json()
        config = body.get("config") or {}
        subject = body.get("subject") or {}
        key = request.header("idempotency-key") or f"{body.get('run_id')}:{body.get('node_id')}"
        try:
            entry = issue(str(config.get("so", "")).strip().upper(), key=f"buoc:{key}",
                          case_id=subject.get("id") if subject.get("type") == "case" else None,
                          summary=str(config.get("trich_yeu", "")), by="Quy trình")  # fmt: skip
        except HttpError as exc:
            return {"branch": "error", "message": exc.message}
        return {"branch": "success", "output": {"so_van_ban": entry["full_number"], "so": entry["number"],
                                                "ngay": entry["issued_at"][:10]}}  # fmt: skip

    # ---- Dossier: tab and action ------------------------------------------------------------------

    @app.route("GET", "/api/ho-so/{case_id}", viewer=True)
    def of_case(request):
        case = app.as_viewer(request).case(request.params["case_id"])
        return {"case": {"id": case["id"], "title": case["title"]}, "books": books(with_next=True), "agency": agency(),
                "entries": db.all("SELECT * FROM entries WHERE case_id = ? ORDER BY issued_at", case["id"])}  # fmt: skip

    @app.route("POST", "/api/ho-so/{case_id}/cap-so", viewer=True)
    def issue_for_case(request):
        require_listed(app, request, "nguoi_cap_so")
        client = app.as_viewer(request)
        case = client.case(request.params["case_id"])  # the viewer must be able to see the dossier
        body = request.json()
        book = str(body.get("so", "")).strip().upper()
        entry = issue(book, key=f"ho-so:{case['id']}:{book}", case_id=case["id"],
                      summary=str(body.get("trich_yeu") or case["title"]), by=request.viewer["user"]["display_name"])  # fmt: skip
        fields = {f["key"] for f in (case.get("form") or {}).get("fields", [])}
        values = {k: v for k, v in {"so_van_ban": entry["full_number"], "ngay_van_ban": entry["issued_at"][:10]}.items()
                  if k in fields}  # fmt: skip
        if values:
            client.write_fields(case["id"], values, key=f"so-van-ban:{entry['id']}")
        return {"entry": entry, "written": sorted(values)}

    # ---- Registers ------------------------------------------------------------------------------

    def listing(request) -> list[dict]:
        year = int(request.query.get("nam") or now().year)
        sql, args = "SELECT * FROM entries WHERE (year = ? OR year = 0)", [year]
        if request.query.get("so"):
            sql, args = sql + " AND book = ?", [*args, request.query["so"].upper()]
        if request.query.get("q"):
            sql, args = sql + " AND (summary LIKE ? OR full_number LIKE ?)", [*args, f"%{request.query['q']}%", f"%{request.query['q']}%"]
        rows = db.all(sql + " ORDER BY book, number DESC LIMIT 1000", *args)
        if (request.viewer.get("context") or {}).get("slot") == "admin.page":
            return rows  # the whole register, for the organisation's managers
        # Everyone else sees the numbers of dossiers they may open, and those they issued themselves.
        client, name, seen = app.as_viewer(request), request.viewer["user"]["display_name"], {}

        def may_open(case_id: str) -> bool:
            if case_id not in seen:
                try:
                    client.case(case_id)
                    seen[case_id] = True
                except PluginError:
                    seen[case_id] = False
            return seen[case_id]

        return [row for row in rows if row["issued_by"] == name or (row["case_id"] and may_open(row["case_id"]))]

    @app.route("GET", "/api/so", viewer=True)
    def registers(request):
        managers = (request.viewer.get("context") or {}).get("slot") == "admin.page"
        return {"books": books(with_next=managers), "agency": agency(), "entries": listing(request)}

    @app.route("GET", "/api/xuat", viewer=True)
    def export(request):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Sổ", "Số, ký hiệu", "Ngày", "Trích yếu", "Người cấp", "Trạng thái", "Lý do huỷ"])
        for entry in listing(request):
            writer.writerow(csv_cells([entry["book"], entry["full_number"], entry["issued_at"][:10], entry["summary"],
                                       entry["issued_by"], "Đã huỷ" if entry["state"] == "cancelled" else "Đã cấp",
                                       entry["cancel_reason"] or ""]))  # fmt: skip
        return Response(200, ("﻿" + out.getvalue()).encode(), "text/csv; charset=utf-8")

    @app.route("POST", "/api/quan-tri/so", admin=True)
    def save_book(request):
        body = request.json()
        code = str(body.get("code", "")).strip().upper()[:10]
        name, symbol = str(body.get("name", "")).strip()[:80], str(body.get("symbol", "")).strip()[:20]
        if not code.isalnum() or not name:
            raise HttpError(422, "Mã sổ chỉ gồm chữ và số; cần tên sổ.")
        start = max(1, int(body.get("start_number") or 1))
        db.run("INSERT INTO books (code, name, symbol, start_number, yearly) VALUES (?, ?, ?, ?, ?) ON CONFLICT (code) "
               "DO UPDATE SET name = excluded.name, symbol = excluded.symbol, start_number = excluded.start_number, "
               "yearly = excluded.yearly", code, name, symbol, start, 1 if body.get("yearly", True) else 0)  # fmt: skip
        return {"code": code}

    @app.route("POST", "/api/quan-tri/huy/{entry_id}", admin=True)
    def cancel(request):
        """Mark a number cancelled (kept in the register, never handed out again)."""
        reason = str(request.json().get("ly_do", "")).strip()[:300]
        if not reason:
            raise HttpError(422, "Nêu lý do huỷ số.")
        db.run("UPDATE entries SET state = 'cancelled', cancel_reason = ? WHERE id = ?", reason, int(request.params["entry_id"]))
        return {"ok": True}

    @app.route("POST", "/events", signed=True)
    def events(request):
        if request.json().get("type") == "plugin.settings.changed":
            app.forget_settings()
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9203)
