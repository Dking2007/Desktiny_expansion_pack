# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Tiếp nhận trực tuyến: people outside the organisation file a request and follow it, without an account.

* /cong/nop.html: choose the procedure, fill in the details, answer a small sum; the page gives back a tracking
  code and a secret. Other systems (a kiosk, another portal) send the same through /api/ngoai/ho-so with a key.
* Each request becomes the event `ho_so_truc_tuyen` in Desktiny; a flow starting on it creates the dossier
  (the "Tạo hồ sơ" step, with the dossier's field `ma_tra_cuu` = {trigger.ma_tra_cuu}).
* Desktiny then tells the plugin about that dossier (submitted, at a step, sent back, approved, rejected, closed);
  the plugin reads its tracking code and keeps the request's status.
* /cong/tra-cuu.html: the code and the secret show the status and its dates, never the dossier's content.

The plugin's server must be reachable from outside for the two public pages; Desktiny itself stays inside.
"""

from __future__ import annotations

import hmac
import random
import re
import secrets
import sys
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "lib"))

from desktiny_plugin import PluginError  # noqa: E402
from mo_rong import App, HttpError, Response, Settings, Store  # noqa: E402

VN = timezone(timedelta(hours=7))
SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
  code TEXT PRIMARY KEY, secret TEXT NOT NULL, procedure TEXT NOT NULL, full_name TEXT NOT NULL, id_number TEXT NOT NULL,
  phone TEXT NOT NULL, address TEXT NOT NULL DEFAULT '', content TEXT NOT NULL DEFAULT '', source TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'received', case_id TEXT, case_code TEXT, step TEXT, created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, code TEXT NOT NULL, status TEXT NOT NULL, note TEXT, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS challenges (id TEXT PRIMARY KEY, answer INTEGER NOT NULL, created REAL NOT NULL);
"""
DEFAULTS = {
    "ten_co_quan": "Bộ phận Một cửa",
    "danh_sach_thu_tuc": "Đăng ký khai sinh; Đăng ký kết hôn; Chứng thực bản sao từ bản chính; "
    "Xác nhận tình trạng hôn nhân; Đăng ký khai tử; Đề nghị hoà giải",
}
STATUS = {
    "received": "Đã nhận, chờ cán bộ tiếp nhận",
    "processing": "Đang xử lý",
    "needs_revision": "Cần bổ sung giấy tờ",
    "approved": "Đã có kết quả, mời đến nhận",
    "rejected": "Không giải quyết",
    "cancelled": "Đã huỷ",
}
EVENT_STATUS = {"case.submitted": "processing", "case.step_entered": "processing", "case.needs_revision": "needs_revision",
                "case.approved": "approved", "case.rejected": "rejected"}  # fmt: skip
ID_NUMBER = re.compile(r"^\d{12}$")
PHONE = re.compile(r"^(0|\+84)\d{9,10}$")


class Window:
    """At most `limit` submissions per address in `seconds`."""

    def __init__(self, limit: int, seconds: int):
        self.limit, self.seconds, self.hits = limit, seconds, {}

    def allow(self, key: str) -> bool:
        now, recent = time.monotonic(), self.hits.setdefault(key, deque())
        while recent and recent[0] < now - self.seconds:
            recent.popleft()
        if len(recent) >= self.limit:
            return False
        recent.append(now)
        return True


def build(settings: Settings | None = None, store: Store | None = None, now=lambda: datetime.now(VN)) -> App:
    app = App("tiep-nhan", HERE, settings)
    db = store or Store(app.settings.data_dir / "tiep-nhan.sqlite3", SCHEMA)
    app.store = db
    window = Window(5, 3600)

    def config() -> dict:
        return app.org_settings(DEFAULTS)

    def procedures() -> list[str]:
        return [p.strip() for p in re.split(r"[;\n]", str(config()["danh_sach_thu_tuc"])) if p.strip()]

    def stamp() -> str:
        return now().isoformat(timespec="seconds")

    def receive(body: dict, source: str) -> dict:
        procedure = str(body.get("thu_tuc", "")).strip()
        if procedure not in procedures():
            raise HttpError(422, "Chọn thủ tục trong danh sách.")
        name = " ".join(str(body.get("ho_ten", "")).split())[:120]
        id_number, phone = str(body.get("so_cccd", "")).strip(), str(body.get("so_dien_thoai", "")).replace(" ", "")
        if len(name) < 3:
            raise HttpError(422, "Nhập họ và tên.")
        if not ID_NUMBER.match(id_number):
            raise HttpError(422, "Số định danh cá nhân (CCCD) gồm 12 chữ số.")
        if not PHONE.match(phone):
            raise HttpError(422, "Số điện thoại chưa đúng.")
        address, content = str(body.get("dia_chi", "")).strip()[:300], str(body.get("noi_dung", "")).strip()[:2000]
        code = f"TN-{now():%y%m}-{secrets.token_hex(3).upper()}"
        secret = f"{secrets.randbelow(10**6):06d}"
        db.run("INSERT INTO requests (code, secret, procedure, full_name, id_number, phone, address, content, source, created_at, "
               "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", code, secret, procedure, name, id_number, phone, address,
               content, source, stamp(), stamp())  # fmt: skip
        db.run("INSERT INTO history (code, status, note, at) VALUES (?, 'received', ?, ?)", code, f"Nộp qua {source}", stamp())
        if app.settings.token:
            app.desktiny.send_event("ho_so_truc_tuyen", {"ma_tra_cuu": code, "thu_tuc": procedure, "ho_ten": name,
                                                         "so_cccd": id_number, "so_dien_thoai": phone, "dia_chi": address,
                                                         "noi_dung": content[:1000]}, key=f"nop:{code}")  # fmt: skip
        return {"ma_tra_cuu": code, "ma_bi_mat": secret, "thu_tuc": procedure}

    # ---- Public pages ---------------------------------------------------------------------------

    @app.route("GET", "/cong/api/thong-tin")
    def info(request):
        challenge_id, a, b = secrets.token_hex(8), random.randint(1, 9), random.randint(1, 9)
        db.run("DELETE FROM challenges WHERE created < ?", time.time() - 1800)
        db.run("INSERT INTO challenges (id, answer, created) VALUES (?, ?, ?)", challenge_id, a + b, time.time())
        return {"co_quan": config()["ten_co_quan"], "thu_tuc": procedures(),
                "cau_hoi": {"id": challenge_id, "noi_dung": f"{a} cộng {b} bằng mấy?"}}  # fmt: skip

    @app.route("POST", "/cong/api/nop")
    def submit(request):
        body = request.json()
        challenge = db.one("SELECT * FROM challenges WHERE id = ?", str(body.get("cau_hoi_id", "")))
        db.run("DELETE FROM challenges WHERE id = ?", str(body.get("cau_hoi_id", "")))
        if not challenge or str(challenge["answer"]) != str(body.get("tra_loi", "")).strip():
            raise HttpError(422, "Câu trả lời kiểm tra chưa đúng; tải lại trang để có câu mới.", "challenge_failed")
        if not window.allow(request.client_ip or "?"):
            raise HttpError(429, "Bạn đã nộp nhiều lần trong giờ qua; thử lại sau.", "too_many")
        return receive(body, "cổng trực tuyến")

    @app.route("GET", "/cong/api/tra-cuu")
    def track(request):
        row = db.one("SELECT * FROM requests WHERE code = ?", request.query.get("ma", "").strip().upper())
        if not row or not hmac.compare_digest(row["secret"], request.query.get("ma_bi_mat", "").strip()):
            raise HttpError(404, "Mã tra cứu hoặc mã bí mật không đúng.")
        return {
            "ma_tra_cuu": row["code"], "thu_tuc": row["procedure"], "ngay_nop": row["created_at"][:10],
            "trang_thai": STATUS.get(row["status"], row["status"]), "ma_ho_so": row["case_code"], "buoc": row["step"],
            "lich_su": [{"trang_thai": STATUS.get(h["status"], h["status"]), "luc": h["at"], "ghi_chu": h["note"]}
                        for h in db.all("SELECT * FROM history WHERE code = ? ORDER BY id", row["code"])],
        }  # fmt: skip

    @app.route("POST", "/api/ngoai/ho-so")
    def from_system(request):
        key = str(config().get("khoa_he_thong_ngoai") or "")
        if not key or not hmac.compare_digest(key, request.header("x-api-key")):
            raise HttpError(401, "Sai khoá hệ thống ngoài.", "api_key_invalid")
        return receive(request.json(), str(request.json().get("nguon") or "hệ thống ngoài")[:60])

    # ---- From Desktiny: the dossier's progress ------------------------------------------------------

    @app.route("POST", "/events", signed=True)
    def events(request):
        body = request.json()
        kind, subject = body.get("type"), body.get("subject") or {}
        if kind == "plugin.settings.changed":
            app.forget_settings()
        if subject.get("type") != "case" or kind not in {*EVENT_STATUS, "case.closed"}:
            return Response(202, b"{}")
        try:
            case = app.desktiny.case(subject["id"])
        except PluginError:
            return Response(202, b"{}")
        code = str((case.get("payload") or {}).get("ma_tra_cuu") or "").strip().upper()
        row = db.one("SELECT * FROM requests WHERE code = ?", code)
        if not row:
            return Response(202, b"{}")
        status = EVENT_STATUS.get(kind) or ("cancelled" if case["status"] == "cancelled" else row["status"])
        step = (body.get("data") or {}).get("step") or row["step"]
        db.run("UPDATE requests SET status = ?, case_id = ?, case_code = ?, step = ?, updated_at = ? WHERE code = ?",
               status, case["id"], case.get("code"), step, stamp(), code)  # fmt: skip
        if status != row["status"]:
            db.run("INSERT INTO history (code, status, note, at) VALUES (?, ?, ?, ?)", code, status, case.get("code"), stamp())
        return Response(202, b"{}")

    # ---- Inside Desktiny ----------------------------------------------------------------------------

    @app.route("GET", "/api/ho-so/{case_id}", viewer=True)
    def for_case(request):
        case = app.as_viewer(request).case(request.params["case_id"])
        code = str((case.get("payload") or {}).get("ma_tra_cuu") or "").strip().upper()
        row = db.one("SELECT code, procedure, source, status, created_at FROM requests WHERE code = ?", code)
        return {"request": {**row, "status_label": STATUS.get(row["status"])} if row else None}

    @app.route("GET", "/api/quan-tri", admin=True)
    def overview(request):
        status = request.query.get("trang_thai")
        sql = "SELECT code, procedure, full_name, phone, source, status, case_code, created_at FROM requests"
        rows = db.all(sql + (" WHERE status = ?" if status else "") + " ORDER BY created_at DESC LIMIT 500", *([status] if status else []))
        return {"items": [{**r, "status_label": STATUS.get(r["status"])} for r in rows], "statuses": STATUS}

    return app


if __name__ == "__main__":
    build().run(9206)
