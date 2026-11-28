# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Cảm biến thiết bị: devices post their readings; a reading past its threshold becomes one Desktiny event.

* A device is registered on the admin page and gets a key, shown once and kept only as a SHA-256 hash. It posts
  `POST /api/so-do` with `X-Device-Key` and `{thiet_bi, chi_so, gia_tri, thoi_diem?}`, at most RATE readings a minute.
* Thresholds are an organisation setting (`nhiet_do>80; do_am>90`). The first reading past one opens an incident
  and queues the event `canh_bao_cam_bien`; later readings past it add nothing until a normal reading closes it.
* Queued events are sent at once and, while Desktiny cannot be reached, again every minute (same idempotency key,
  so a resend is never a second event). A flow starting on the event creates the incident dossier.
* Readings and closed incidents older than `luu_ngay` days are deleted every round.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "lib"))

from desktiny_plugin import PluginError  # noqa: E402
from mo_rong import App, HttpError, Response, Settings, Store, Window  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, location TEXT NOT NULL DEFAULT '', key_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY, device TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL,
                                     at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS readings_series ON readings (device, metric, id);
CREATE INDEX IF NOT EXISTS readings_at ON readings (at);
CREATE TABLE IF NOT EXISTS incidents (
  id INTEGER PRIMARY KEY, device TEXT NOT NULL, metric TEXT NOT NULL, rule TEXT NOT NULL, value REAL NOT NULL,
  opened_at TEXT NOT NULL, closed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS incidents_open ON incidents (device, metric) WHERE closed_at IS NULL;
CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, key TEXT UNIQUE NOT NULL, type TEXT NOT NULL, data TEXT NOT NULL,
                                   created_at TEXT NOT NULL, error TEXT);
"""
DEFAULTS = {"nguong": "nhiet_do>80; do_am>90", "nguoi_phu_trach": "", "luu_ngay": 30}
EVENT = "canh_bao_cam_bien"
RATE = 30  # readings per device per minute
DEVICE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
METRIC = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
RULE = re.compile(r"^([a-z][a-z0-9_]{0,39})\s*([<>])\s*(-?\d+(?:[.,]\d+)?)$")
SERIES = 30  # points per chart on the home block


def rules(spec) -> dict[str, list[tuple[str, float]]]:
    """'nhiet_do>80; nhiet_do<5; do_am>90' → {'nhiet_do': [('>', 80), ('<', 5)], …}; parts not of that shape are skipped."""
    found: dict[str, list[tuple[str, float]]] = {}
    for part in re.split(r"[;\n]", str(spec)):
        match = RULE.match(part.strip())
        if match:
            found.setdefault(match[1], []).append((match[2], float(match[3].replace(",", "."))))
    return found


def crossed(value: float, limits: list[tuple[str, float]]) -> str | None:
    """The first threshold the value is past, as text ('> 80'), or None when it is normal."""
    for sign, limit in limits:
        if (value > limit) if sign == ">" else (value < limit):
            return f"{sign} {limit:g}"
    return None


def digest(key: str) -> str:
    # Keys are 32 random bytes, so a plain hash is enough (no password stretching needed).
    return hashlib.sha256(key.encode()).hexdigest()


def build(settings: Settings | None = None, store: Store | None = None, now=lambda: datetime.now(timezone.utc)) -> App:
    app = App("cam-bien", HERE, settings)
    db = store or Store(app.settings.data_dir / "cam-bien.sqlite3", SCHEMA)
    app.store = db
    window = Window(RATE, 60)

    def config() -> dict:
        return app.org_settings(DEFAULTS)

    def utc(moment: datetime) -> str:
        return moment.astimezone(timezone.utc).isoformat(timespec="seconds")

    def moment(value) -> str:
        if value in (None, ""):
            return utc(now())
        try:
            at = datetime.fromisoformat(str(value))
        except ValueError:
            raise HttpError(422, "thoi_diem theo ISO 8601, ví dụ 2026-11-28T08:00:00+07:00.") from None
        if at.tzinfo is None:
            raise HttpError(422, "thoi_diem cần ghi múi giờ, ví dụ +07:00.")
        if at > now() + timedelta(minutes=5):
            raise HttpError(422, "thoi_diem ở tương lai; kiểm tra đồng hồ của thiết bị.")
        return utc(at)

    # ---- Events to Desktiny, kept until delivered -------------------------------------------------

    def flush() -> int:
        """Send what is queued, oldest first; stop at the first sign Desktiny is down and keep the rest."""
        if not app.settings.token:
            return 0
        sent = 0
        for row in db.all("SELECT * FROM outbox WHERE error IS NULL ORDER BY id LIMIT 100"):
            try:
                app.desktiny.send_event(row["type"], json.loads(row["data"]), key=row["key"])
            except PluginError as exc:
                if exc.status != 422:  # down, busy, or a token being replaced: try again next round
                    break
                # This event refused for good (e.g. the manifest changed): kept with the reason, shown on the admin page.
                db.run("UPDATE outbox SET error = ? WHERE id = ?", f"{exc.status} {exc.code}: {exc.detail}"[:300], row["id"])
                continue
            except OSError:
                break
            db.run("DELETE FROM outbox WHERE id = ?", row["id"])
            sent += 1
        return sent

    def prune() -> None:
        days = max(1, int(float(config()["luu_ngay"] or DEFAULTS["luu_ngay"])))
        cutoff = utc(now() - timedelta(days=days))
        db.run("DELETE FROM readings WHERE at < ?", cutoff)
        db.run("DELETE FROM incidents WHERE closed_at IS NOT NULL AND closed_at < ?", cutoff)

    def round_() -> dict:
        sent = flush()
        prune()
        return {"sent": sent}

    app.round = round_
    if app.settings.token:
        app.every(lambda: 60, round_)

    # ---- Devices post readings ------------------------------------------------------------------

    def judge(device: dict, metric: str, value: float, at: str) -> str | None:
        """Open an incident (and queue its event) on the first reading past a threshold; close it on a normal one."""
        settings = config()  # read before the lock: it may ask Desktiny
        rule = crossed(value, rules(settings["nguong"]).get(metric, []))
        with db.transaction() as tx:
            current = tx.execute("SELECT id FROM incidents WHERE device = ? AND metric = ? AND closed_at IS NULL",
                                 (device["id"], metric)).fetchone()  # fmt: skip
            if current and not rule:
                tx.execute("UPDATE incidents SET closed_at = ? WHERE id = ?", (at, current["id"]))
                return "closed"
            if current or not rule:
                return "open" if current else None
            incident = tx.execute("INSERT INTO incidents (device, metric, rule, value, opened_at) VALUES (?, ?, ?, ?, ?)",
                                  (device["id"], metric, rule, value, at)).lastrowid  # fmt: skip
            data = {"thiet_bi": device["id"], "ten_thiet_bi": device["name"], "vi_tri": device["location"], "chi_so": metric,
                    "gia_tri": value, "nguong": rule, "thoi_diem": at, "nguoi_phu_trach": str(settings["nguoi_phu_trach"])}  # fmt: skip
            tx.execute("INSERT INTO outbox (key, type, data, created_at) VALUES (?, ?, ?, ?)",
                       (f"su-co:{incident}", EVENT, json.dumps(data, ensure_ascii=False), utc(now())))  # fmt: skip
        # shortcut: sent in the device's request (a slow Desktiny delays that one reply), fine at one send per incident.
        flush()
        return "opened"

    @app.route("POST", "/api/so-do")
    def reading(request):
        body = request.json()
        key = request.header("x-device-key")
        if not key:
            raise HttpError(401, "Thiếu khoá thiết bị (X-Device-Key).", "device_key_missing")
        device = db.one("SELECT * FROM devices WHERE id = ?", str(body.get("thiet_bi", "")).strip())
        if not device or not hmac.compare_digest(device["key_hash"], digest(key)):
            raise HttpError(403, "Mã thiết bị hoặc khoá không đúng.", "device_key_invalid")
        if not window.allow(device["id"]):
            raise HttpError(429, f"Thiết bị gửi quá {RATE} số đo mỗi phút.", "too_many")
        metric, value = str(body.get("chi_so", "")).strip(), body.get("gia_tri")
        if not METRIC.match(metric):
            raise HttpError(422, "chi_so là chữ thường không dấu, số, gạch dưới (ví dụ nhiet_do).")
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
            raise HttpError(422, "gia_tri phải là một số.")
        at = moment(body.get("thoi_diem"))
        db.run("INSERT INTO readings (device, metric, value, at) VALUES (?, ?, ?, ?)", device["id"], metric, float(value), at)
        return {"ok": True, "thoi_diem": at, "su_co": judge(device, metric, float(value), at)}

    # ---- Inside Desktiny ------------------------------------------------------------------------

    @app.route("GET", "/api/tong-quan", viewer=True)
    def overview(request):
        """Each device's latest value per metric, with the last readings for a small chart."""
        limits, items = rules(config()["nguong"]), []
        for device in db.all("SELECT id, name, location FROM devices ORDER BY name LIMIT 50"):
            open_ = {r["metric"] for r in db.all("SELECT metric FROM incidents WHERE device = ? AND closed_at IS NULL", device["id"])}
            metrics = []
            for row in db.all("SELECT metric, value, at FROM readings WHERE id IN (SELECT MAX(id) FROM readings WHERE device = ? "
                              "GROUP BY metric) ORDER BY metric LIMIT 10", device["id"]):  # fmt: skip
                series = db.all("SELECT value FROM readings WHERE device = ? AND metric = ? ORDER BY id DESC LIMIT ?",
                                device["id"], row["metric"], SERIES)  # fmt: skip
                metrics.append({**row, "alert": row["metric"] in open_, "series": [r["value"] for r in reversed(series)],
                                "limits": [f"{s} {v:g}" for s, v in limits.get(row["metric"], [])]})  # fmt: skip
            items.append({**device, "metrics": metrics})
        return {"items": items}

    @app.route("GET", "/api/quan-tri", admin=True)
    def admin(request):
        devices = db.all("SELECT d.id, d.name, d.location, d.created_at, (SELECT MAX(at) FROM readings WHERE device = d.id) AS last_at, "
                         "(SELECT COUNT(*) FROM incidents WHERE device = d.id AND closed_at IS NULL) AS open FROM devices d ORDER BY d.name")  # fmt: skip
        return {"devices": devices, "thresholds": rules(config()["nguong"]), "settings": config(), "rate": RATE,
                "incidents": db.all("SELECT * FROM incidents ORDER BY id DESC LIMIT 50"),
                "pending": db.one("SELECT COUNT(*) AS n FROM outbox WHERE error IS NULL")["n"],
                "failed": db.all("SELECT key, error, created_at FROM outbox WHERE error IS NOT NULL ORDER BY id DESC LIMIT 20")}  # fmt: skip

    @app.route("POST", "/api/quan-tri/thiet-bi", admin=True)
    def register(request):
        body = request.json()
        device_id, name = str(body.get("ma", "")).strip().lower(), " ".join(str(body.get("ten", "")).split())[:120]
        if not DEVICE.match(device_id):
            raise HttpError(422, "Mã thiết bị gồm chữ thường không dấu, số, gạch ngang (tối đa 40 ký tự).")
        if not name:
            raise HttpError(422, "Nhập tên thiết bị.")
        key = secrets.token_urlsafe(32)
        try:
            db.run("INSERT INTO devices (id, name, location, key_hash, created_at) VALUES (?, ?, ?, ?, ?)", device_id, name,
                   str(body.get("vi_tri", "")).strip()[:200], digest(key), utc(now()))  # fmt: skip
        except sqlite3.IntegrityError as exc:
            raise HttpError(409, f"Đã có thiết bị mã “{device_id}”.", "device_exists") from exc
        return {"ma": device_id, "khoa": key}

    @app.route("POST", "/api/quan-tri/thiet-bi/{device_id}/khoa", admin=True)
    def new_key(request):
        key = secrets.token_urlsafe(32)
        if not db.one("SELECT id FROM devices WHERE id = ?", request.params["device_id"]):
            raise HttpError(404, "Không có thiết bị này.", "not_found")
        db.run("UPDATE devices SET key_hash = ? WHERE id = ?", digest(key), request.params["device_id"])
        return {"ma": request.params["device_id"], "khoa": key}

    @app.route("POST", "/events", signed=True)
    def events(request):
        if request.json().get("type") == "plugin.settings.changed":
            app.forget_settings()
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9208)
