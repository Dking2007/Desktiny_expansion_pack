# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Nhắc hạn: watch a date field (contract end, permit expiry, certificate validity) in the dossiers of the
processes an administrator chose, and remind the dossier's owner before it passes.

Each round reads only dossiers changed since the last one (`cases.list` with `updated_since`) and keeps their
dates; the reminders are worked out from the kept dates, so a dossier untouched for a year is still reminded.
At each threshold (by default 30, 7 and 1 days before, and on the day) the owner gets a notice once, and Desktiny
gets the event `sap_het_han`, which a flow may start on (create a renewal task, tell the unit head…).
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "lib"))

from desktiny_plugin import Client, PluginError  # noqa: E402
from mo_rong import App, Response, Settings, Store  # noqa: E402
from mo_rong.vn import parse_date  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS watched (
  case_id TEXT PRIMARY KEY, code TEXT NOT NULL, title TEXT NOT NULL, owner_id TEXT, owner_name TEXT,
  expires TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminded (key TEXT PRIMARY KEY, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
DEFAULTS = {"truong_ngay_het_han": "ngay_het_han", "moc_nhac": "30,7,1,0", "chu_ky_phut": 60}
CLOSED = {"cancelled", "rejected"}
MAX_PER_ROUND = 2000
ADMIN_CAP = 500  # rows on the admin page; the counts cover every watched dossier


def thresholds(spec) -> list[int]:
    values = sorted({int(part) for part in str(spec).split(",") if part.strip().lstrip("-").isdigit()}, reverse=True)
    return values or [30, 7, 1, 0]


def build(settings: Settings | None = None, store: Store | None = None, today=date.today) -> App:
    app = App("nhac-han", HERE, settings)
    db = store or Store(app.settings.data_dir / "nhac-han.sqlite3", SCHEMA)
    app.store = db

    def config() -> dict:
        return app.org_settings(DEFAULTS)

    def sync() -> int:
        """Read the dossiers changed since the last round and keep the date each one carries."""
        field = str(config()["truong_ngay_het_han"]).strip()
        last = db.one("SELECT value FROM state WHERE name = 'since'")
        started = datetime.now(timezone.utc).isoformat()
        cursor, seen = None, 0
        while seen < MAX_PER_ROUND:
            page = app.desktiny.cases(updated_since=last["value"] if last else None, cursor=cursor, limit=200)
            for item in page["items"]:
                seen += 1
                try:
                    case = app.desktiny.case(item["id"])
                except PluginError:
                    continue
                expires = parse_date((case.get("payload") or {}).get(field))
                if not expires or case["status"] in CLOSED:
                    db.run("DELETE FROM watched WHERE case_id = ?", case["id"])
                    continue
                owner = case.get("owner") or {}
                db.run("INSERT INTO watched (case_id, code, title, owner_id, owner_name, expires, status) VALUES "
                       "(?, ?, ?, ?, ?, ?, ?) ON CONFLICT (case_id) DO UPDATE SET code = excluded.code, title = excluded.title, "
                       "owner_id = excluded.owner_id, owner_name = excluded.owner_name, expires = excluded.expires, "
                       "status = excluded.status", case["id"], case.get("code", ""), case["title"], owner.get("id"),
                       owner.get("display_name"), expires.isoformat(), case["status"])  # fmt: skip
            cursor = page.get("next_cursor")
            if not cursor:
                break
        db.run("INSERT INTO state (name, value) VALUES ('since', ?) ON CONFLICT (name) DO UPDATE SET value = excluded.value",
               started)  # fmt: skip
        return seen

    def remind() -> list[dict]:
        """Notices and events for every dossier at one of the thresholds, each once."""
        marks, now, sent = thresholds(config()["moc_nhac"]), today(), []
        for row in db.all("SELECT * FROM watched"):
            left = (date.fromisoformat(row["expires"]) - now).days
            reached = [mark for mark in marks if left <= mark]
            if not reached:
                continue
            mark = min(reached)  # the nearest threshold reached; earlier ones missed are not sent late
            key = f"{row['case_id']}:{row['expires']}:{mark}"
            if db.one("SELECT key FROM reminded WHERE key = ?", key):
                continue
            db.run("INSERT INTO reminded (key, at) VALUES (?, ?)", key, now.isoformat())
            when = "hôm nay" if left == 0 else (f"đã quá {-left} ngày" if left < 0 else f"còn {left} ngày")
            if row["owner_id"]:
                app.desktiny.notify(f"Sắp hết hạn ({when}): {row['title']}"[:200], [row["owner_id"]], case_id=row["case_id"],
                                    link=f"/cases/{row['case_id']}", key=f"nhac:{key}")  # fmt: skip
            app.desktiny.send_event("sap_het_han", {"ho_so": row["case_id"], "ngay_het_han": row["expires"], "con_lai": left},
                                    key=f"su-kien:{key}")  # fmt: skip
            sent.append({**row, "left": left})
        return sent

    def round_() -> dict:
        return {"read": sync(), "reminded": len(remind())}

    app.round = round_
    if app.settings.token:
        app.every(lambda: float(config()["chu_ky_phut"]) * 60, round_)

    def upcoming(days: int, client: Client | None = None, cap: int = 50) -> list[dict]:
        rows = db.all("SELECT * FROM watched ORDER BY expires")
        limit = today().toordinal() + days
        result = []
        for row in rows:
            if date.fromisoformat(row["expires"]).toordinal() > limit:
                break
            if client is not None:  # only dossiers this person may open
                try:
                    client.case(row["case_id"])
                except PluginError:
                    continue
            result.append({**row, "left": (date.fromisoformat(row["expires"]) - today()).days})
            if len(result) >= cap:
                break
        return result

    def sent_marks(item: dict) -> list[dict]:
        """The thresholds already reminded for this dossier's current date, nearest last."""
        prefix = f"{item['case_id']}:{item['expires']}:"
        rows = db.all("SELECT key, at FROM reminded WHERE substr(key, 1, ?) = ?", len(prefix), prefix)
        marks = [{"mark": int(r["key"][len(prefix):]), "at": r["at"]} for r in rows if r["key"][len(prefix):].lstrip("-").isdigit()]
        return sorted(marks, key=lambda m: -m["mark"])

    def counts() -> dict:
        """How many watched dossiers fall in each band, over all of them (the list itself is capped)."""
        result = {"overdue": 0, "d7": 0, "d30": 0, "d90": 0, "later": 0}
        now = today()
        for row in db.all("SELECT expires FROM watched"):
            left = (date.fromisoformat(row["expires"]) - now).days
            band = "overdue" if left < 0 else "d7" if left <= 7 else "d30" if left <= 30 else "d90" if left <= 90 else "later"
            result[band] += 1
        return result

    @app.route("GET", "/api/sap-het-han", viewer=True)
    def mine(request):
        days = max(1, min(365, int(request.query.get("ngay") or 30)))
        return {"items": upcoming(days, app.as_viewer(request)), "field": config()["truong_ngay_het_han"],
                "marks": thresholds(config()["moc_nhac"]), "today": today().isoformat()}  # fmt: skip

    @app.route("GET", "/api/quan-tri", admin=True)
    def overview(request):
        last = db.one("SELECT value FROM state WHERE name = 'since'")
        days = max(1, min(3660, int(request.query.get("ngay") or 90)))
        items = [{**item, "reminded": sent_marks(item)} for item in upcoming(days, cap=ADMIN_CAP)]
        return {"items": items, "watched": db.one("SELECT COUNT(*) AS n FROM watched")["n"],
                "last_round": last["value"] if last else None, "settings": config(), "marks": thresholds(config()["moc_nhac"]),
                "counts": counts(), "truncated": len(items) >= ADMIN_CAP, "today": today().isoformat()}  # fmt: skip

    @app.route("POST", "/api/quan-tri/quet", admin=True)
    def scan_now(request):
        return round_()

    @app.route("POST", "/tools/sap-het-han", signed=True)
    def tool(request):
        body = request.json()
        days = max(1, min(365, int((body.get("arguments") or {}).get("so_ngay") or 30)))
        client = app.client_factory(body.get("token") or "")
        items = upcoming(days, client)
        return {"result": [{"ho_so": f"{r['code']} {r['title']}", "het_han": r["expires"], "con_lai_ngay": r["left"]} for r in items]}

    @app.route("POST", "/events", signed=True)
    def events(request):
        if request.json().get("type") == "plugin.settings.changed":
            app.forget_settings()
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9205)
