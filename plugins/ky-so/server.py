# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Ký số: sign a dossier's documents and attach a signing receipt, from a flow step or a dossier button.

* The flow step "Ký số văn bản" (`mode: async`) queues the dossier's files for signing and waits; the signer opens
  "Văn bản chờ ký", checks the files and confirms with a personal PIN; the receipt is attached to the dossier at that
  step and the flow goes on (or takes its error exit when the signer refuses).
* The dossier button "Ký số" signs at once, as the person looking at it.
* Anyone can check a receipt's code at /cong/xac-thuc.html (who signed what, when, and the file's SHA-256).

The signature here is an HMAC under the organisation's key: a stand-in that keeps the whole path (queue, PIN,
receipt, verification) working. A real signature (a certificate from a licensed provider, a USB token or remote
signing) replaces `Signer.sign` and `Signer.check`; nothing else changes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "lib"))

from mo_rong import App, HttpError, Response, Settings, Store  # noqa: E402
from mo_rong.pdf import one_page  # noqa: E402

VN = timezone(timedelta(hours=7))
PAGE_LINK = "/apps/vn.mo-rong.ky-so/0"
SCHEMA = """
CREATE TABLE IF NOT EXISTS pins (user_id TEXT PRIMARY KEY, salt TEXT NOT NULL, hash TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS requests (
  call_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, node_id TEXT NOT NULL, title TEXT NOT NULL,
  signer_id TEXT, reason TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT 'waiting', created_at TEXT NOT NULL,
  done_at TEXT, done_by TEXT
);
CREATE TABLE IF NOT EXISTS signatures (
  code TEXT PRIMARY KEY, case_id TEXT NOT NULL, file_id TEXT NOT NULL, file_name TEXT NOT NULL, sha256 TEXT NOT NULL,
  signer_id TEXT NOT NULL, signer_name TEXT NOT NULL, signed_at TEXT NOT NULL, signature TEXT NOT NULL,
  receipt_id TEXT, call_id TEXT
);
"""


class Signer:
    """HMAC-SHA256 under the organisation's key (setting `khoa_ky`): a stand-in for a certificate signature."""

    def __init__(self, key: str):
        if not key:
            raise HttpError(409, "Chưa đặt khoá ký của cơ quan (Quản trị › Plugin › Cấu hình).", "key_missing")
        self.key = key.encode()

    def sign(self, digest: str, signer_id: str, at: str) -> str:
        return hmac.new(self.key, f"{digest}|{signer_id}|{at}".encode(), hashlib.sha256).hexdigest()

    def check(self, digest: str, signer_id: str, at: str, signature: str) -> bool:
        return hmac.compare_digest(self.sign(digest, signer_id, at), signature)


def pin_hash(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()


def build(settings: Settings | None = None, store: Store | None = None, now=lambda: datetime.now(VN)) -> App:
    app = App("ky-so", HERE, settings)
    db = store or Store(app.settings.data_dir / "ky-so.sqlite3", SCHEMA)
    app.store = db

    def signer() -> Signer:
        return Signer(str(app.org_settings().get("khoa_ky") or ""))

    def check_pin(user_id: str, pin: str):
        row = db.one("SELECT * FROM pins WHERE user_id = ?", user_id)
        if not row:
            raise HttpError(409, "Đặt mã PIN ký trước khi ký.", "pin_missing")
        if row["failures"] >= 5:
            raise HttpError(423, "Nhập sai PIN quá 5 lần; nhờ quản trị đặt lại.", "pin_locked")
        if not hmac.compare_digest(pin_hash(pin, row["salt"]), row["hash"]):
            db.run("UPDATE pins SET failures = failures + 1 WHERE user_id = ?", user_id)
            raise HttpError(403, "Sai mã PIN.", "pin_wrong")
        db.run("UPDATE pins SET failures = 0 WHERE user_id = ?", user_id)

    def sign_files(client, case: dict, file_ids: list[str] | None, user: dict, *, node_id=None, call_id=None) -> dict:
        """Sign the chosen files (all when None) and attach one receipt; `client` reads and attaches."""
        files = [f for f in client.case_files(case["id"]) if file_ids is None or f["id"] in file_ids]
        files = [f for f in files if not f["name"].startswith("xac-nhan-ky-so")]
        if not files:
            raise HttpError(422, "Hồ sơ không có tài liệu để ký.")
        at = now().isoformat(timespec="seconds")
        lines, codes = [f"Ho so: {case.get('code', '')} {case['title']}", f"Nguoi ky: {user['display_name']}",
                        f"Thoi diem ky: {at}", ""], []  # fmt: skip
        tool = signer()
        for item in files:
            digest = hashlib.sha256(client.file_content(case["id"], item["id"])).hexdigest()
            code = secrets.token_hex(6).upper()
            db.run("INSERT INTO signatures (code, case_id, file_id, file_name, sha256, signer_id, signer_name, signed_at, "
                   "signature, call_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", code, case["id"], item["id"], item["name"],
                   digest, user["id"], user["display_name"], at, tool.sign(digest, user["id"], at), call_id)  # fmt: skip
            codes.append(code)
            lines += [f"Tep: {item['name']}", f"  SHA-256: {digest}", f"  Ma xac thuc: {code}", ""]
        lines += ["Kiem tra ma xac thuc tai trang Xac thuc chu ky cua co quan (/cong/xac-thuc.html).",
                  "Chu ky mo phong bang khoa cua co quan; thay bang chung thu so khi trien khai that."]  # fmt: skip
        receipt = one_page("PHIEU XAC NHAN KY SO", lines)
        name = f"xac-nhan-ky-so-{codes[0].lower()}.pdf"
        attached = client.attach(case["id"], name, receipt, "application/pdf", node_id=node_id, role="result",
                                 key=f"ky-so:{case['id']}:{codes[0]}")  # fmt: skip
        db.run(f"UPDATE signatures SET receipt_id = ? WHERE code IN ({','.join('?' * len(codes))})", attached.get("id"), *codes)
        return {"signed": len(codes), "codes": codes, "receipt": name, "at": at}

    # ---- PIN ------------------------------------------------------------------------------------

    @app.route("GET", "/api/toi", viewer=True)
    def me(request):
        row = db.one("SELECT failures FROM pins WHERE user_id = ?", request.viewer["user"]["id"])
        return {"user": request.viewer["user"], "has_pin": bool(row), "locked": bool(row and row["failures"] >= 5)}

    @app.route("POST", "/api/pin", viewer=True)
    def set_pin(request):
        body = request.json()
        user_id = request.viewer["user"]["id"]
        pin = str(body.get("pin", ""))
        if not pin.isdigit() or not 6 <= len(pin) <= 12:
            raise HttpError(422, "PIN gồm 6–12 chữ số.")
        if db.one("SELECT user_id FROM pins WHERE user_id = ?", user_id):
            check_pin(user_id, str(body.get("pin_cu", "")))
        salt = secrets.token_hex(16)
        db.run("INSERT INTO pins (user_id, salt, hash) VALUES (?, ?, ?) ON CONFLICT (user_id) DO UPDATE SET "
               "salt = excluded.salt, hash = excluded.hash, failures = 0", user_id, salt, pin_hash(pin, salt))  # fmt: skip
        return {"ok": True}

    @app.route("POST", "/api/quan-tri/mo-khoa-pin", admin=True)
    def reset_pin(request):
        db.run("DELETE FROM pins WHERE user_id = ?", str(request.json().get("user_id", "")))
        return {"ok": True}

    # ---- Flow step: queue and wait ----------------------------------------------------------------

    @app.route("POST", "/nodes/ky-so", signed=True)
    def step(request):
        body = request.json()
        subject = body.get("subject") or {}
        if subject.get("type") != "case":
            return {"branch": "error", "message": "Bước ký số cần chạy trên một hồ sơ."}
        config = body.get("config") or {}
        case = app.desktiny.case(subject["id"])
        signer_id = str(config.get("nguoi_ky") or "").strip() or None
        db.run("INSERT OR IGNORE INTO requests (call_id, case_id, node_id, title, signer_id, reason, created_at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?)", body["call_id"], case["id"], body.get("node_id", ""), case["title"],
               signer_id, str(config.get("ghi_chu") or "")[:300], now().isoformat(timespec="seconds"))  # fmt: skip
        if signer_id:
            app.desktiny.notify(f"Có văn bản chờ ký: {case['title']}"[:200], [signer_id], link=PAGE_LINK,
                                key=f"cho-ky:{body['call_id']}")  # fmt: skip
        return Response(202, json.dumps({"accepted": True}).encode())

    def visible_requests(request) -> list[dict]:
        client, user_id = app.as_viewer(request), request.viewer["user"]["id"]
        mine = []
        for row in db.all("SELECT * FROM requests WHERE state = 'waiting' ORDER BY created_at"):
            if row["signer_id"] and row["signer_id"] != user_id:
                continue
            try:
                client.case(row["case_id"])  # only dossiers the viewer may see
            except Exception:  # noqa: BLE001 (not visible to this person)
                continue
            mine.append(row)
        return mine

    @app.route("GET", "/api/cho-ky", viewer=True)
    def waiting(request):
        result = []
        for row in visible_requests(request):
            files = app.desktiny.case_files(row["case_id"])
            result.append({**row, "files": [f for f in files if not f["name"].startswith("xac-nhan-ky-so")]})
        return {"items": result}

    @app.route("POST", "/api/cho-ky/{call_id}", viewer=True)
    def decide(request):
        row = next((r for r in visible_requests(request) if r["call_id"] == request.params["call_id"]), None)
        if not row:
            raise HttpError(404, "Không có yêu cầu ký này, hoặc bạn không phải người ký.")
        body = request.json()
        user = request.viewer["user"]
        check_pin(user["id"], str(body.get("pin", "")))
        if body.get("tu_choi"):
            reason = str(body.get("ly_do") or "Người ký từ chối.")[:300]
            db.run("UPDATE requests SET state = 'refused', done_at = ?, done_by = ? WHERE call_id = ?",
                   now().isoformat(timespec="seconds"), user["display_name"], row["call_id"])  # fmt: skip
            app.desktiny.complete_call(row["call_id"], "error", {}, reason)
            return {"state": "refused"}
        case = app.desktiny.case(row["case_id"])
        result = sign_files(app.desktiny, case, body.get("file_ids"), user, node_id=row["node_id"], call_id=row["call_id"])
        db.run("UPDATE requests SET state = 'signed', done_at = ?, done_by = ? WHERE call_id = ?",
               result["at"], user["display_name"], row["call_id"])  # fmt: skip
        app.desktiny.complete_call(row["call_id"], "success",
                                   {"so_tep_da_ky": result["signed"], "ma_xac_thuc": result["codes"][0],
                                    "nguoi_ky": user["display_name"]}, f"{user['display_name']} đã ký {result['signed']} tệp.")  # fmt: skip
        return {"state": "signed", **result}

    # ---- Dossier button: sign now -----------------------------------------------------------------

    @app.route("GET", "/api/ho-so/{case_id}", viewer=True)
    def case_files(request):
        client = app.as_viewer(request)
        case = client.case(request.params["case_id"])
        return {"case": {"id": case["id"], "title": case["title"]},
                "files": [f for f in client.case_files(case["id"]) if not f["name"].startswith("xac-nhan-ky-so")],
                "signatures": db.all("SELECT code, file_name, signer_name, signed_at FROM signatures WHERE case_id = ? "
                                     "ORDER BY signed_at", case["id"])}  # fmt: skip

    @app.route("POST", "/api/ho-so/{case_id}/ky", viewer=True)
    def sign_now(request):
        client = app.as_viewer(request)
        case = client.case(request.params["case_id"])
        body = request.json()
        check_pin(request.viewer["user"]["id"], str(body.get("pin", "")))
        return sign_files(client, case, body.get("file_ids"), request.viewer["user"])

    # ---- Public verification ----------------------------------------------------------------------

    @app.route("GET", "/xac-thuc/{code}")
    def verify_code(request):
        row = db.one("SELECT * FROM signatures WHERE code = ?", request.params["code"].strip().upper())
        if not row:
            raise HttpError(404, "Không có mã xác thực này.")
        valid = signer().check(row["sha256"], row["signer_id"], row["signed_at"], row["signature"])
        return {"valid": valid, "file_name": row["file_name"], "sha256": row["sha256"], "signer": row["signer_name"],
                "signed_at": row["signed_at"]}  # fmt: skip

    @app.route("POST", "/events", signed=True)
    def events(request):
        body = request.json()
        if body.get("type") == "plugin.settings.changed":
            app.forget_settings()
        if body.get("type") == "plugin.call.cancelled":
            db.run("UPDATE requests SET state = 'cancelled' WHERE call_id = ?", (body.get("subject") or {}).get("id"))
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9204)
