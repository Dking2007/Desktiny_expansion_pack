# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Lưu trữ lịch sử: when a dossier is approved or closed, keep a redacted copy of it, outside Desktiny's live data.

Each copy is one JSON line appended to `archive/YYYY-MM.jsonl` (the month it was archived): the dossier's id and
code, its form, its version (Desktiny's `updated_at`), the event and its time, the payload with personal numbers
masked, `sha256` of that payload as canonical JSON, and `prev`, the sha256 of the line before it (across months).
Changing any line breaks the chain at the line after it; `verify` finds the first break.

An illustration of a data lifecycle and lineage, not a data lake: plain files, no columnar storage, no query
engine. The chain shows edits; it cannot stop someone with write access to the files from rewriting all of them
(keep the head hash shown on the admin page somewhere else to catch that).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "lib"))

from desktiny_plugin import PluginError  # noqa: E402
from mo_rong import App, HttpError, Response, Settings  # noqa: E402

EVENTS = {"case.approved", "case.closed"}
DEFAULTS = {"giu_thang": 12}
GENESIS = "0" * 64
MONTH = re.compile(r"^\d{4}-\d{2}$")

# Order matters: 12-digit CCCD before 10-digit phones, e-mails before either (an address may hold digits).
PII = [
    ("[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("[CCCD]", re.compile(r"(?<!\d)\d{12}(?!\d)")),
    ("[SĐT]", re.compile(r"(?<![\d+])(?:\+84|0)(?:[ .-]?\d){9}(?!\d)")),
    ("[CMND]", re.compile(r"(?<!\d)\d{9}(?!\d)")),
]


def redact(value):
    """The same structure with e-mails, CCCD (12 digits), old CMND (9 digits) and Vietnamese phone numbers masked
    in every string. Pattern-based: names, addresses, dates of birth and numbers written another way stay as they
    are; any other 9- or 12-digit number (a bank account, say) is masked too."""
    if isinstance(value, str):
        for token, pattern in PII:
            value = pattern.sub(token, value)
        return value
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def months_before(month: str, n: int) -> str:
    """'2026-11' minus n months."""
    year, mon = map(int, month.split("-"))
    total = year * 12 + mon - 1 - n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def build(settings: Settings | None = None, now=lambda: datetime.now(timezone.utc)) -> App:
    app = App("luu-tru-lich-su", HERE, settings)
    folder = app.settings.data_dir / "archive"
    folder.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    # shortcut: the index lives in memory, rebuilt from the files at start; move it to SQLite past ~10^6 lines.
    seen: set[tuple] = set()
    by_code: dict[str, list[dict]] = {}
    lines: dict[str, int] = {}
    head = {"hash": GENESIS}

    def files() -> list[Path]:
        return sorted(p for p in folder.glob("*.jsonl") if MONTH.match(p.stem))

    def remember(entry: dict, month: str, line: int):
        seen.add((entry["case_id"], entry["version"], entry["event"]))
        by_code.setdefault(str(entry.get("code") or "").upper(), []).append({**entry, "month": month, "line": line})
        lines[month] = line

    for path in files():  # the files are the record; the index is only rebuilt from them
        for number, raw in enumerate(path.read_bytes().splitlines(), 1):
            lines[path.stem], head["hash"] = number, sha256(raw)
            try:
                remember(json.loads(raw), path.stem, number)
            except (ValueError, KeyError, TypeError):
                continue  # a damaged line: the plugin still starts, and verify() points at it

    def archive(event: dict, case: dict) -> bool:
        """Append one line for this dossier version and event; False if it is already there (a replay)."""
        version = str(case.get("revision") or case.get("updated_at") or "")
        key = (case["id"], version, event["type"])
        with lock:
            if key in seen:
                return False
            payload = redact(case.get("payload") or {})
            at = now()
            entry = {"case_id": case["id"], "code": case.get("code", ""), "title": redact(case.get("title", "")),
                     "form_id": (case.get("form") or {}).get("id"), "form_name": (case.get("form") or {}).get("name"),
                     "version": version, "event": event["type"], "event_id": event.get("event_id"),
                     "occurred_at": event.get("occurred_at"), "archived_at": at.isoformat(), "payload": payload,
                     "sha256": sha256(canonical(payload)), "prev": head["hash"]}  # fmt: skip
            raw = json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode()
            path = folder / f"{at:%Y-%m}.jsonl"
            with path.open("ab+") as out:
                end = out.seek(0, 2)
                if end:
                    out.seek(end - 1)
                    if out.read(1) != b"\n":  # a line cut short by a crash stays apart; verify() reports it
                        out.write(b"\n")
                out.write(raw + b"\n")
            head["hash"] = sha256(raw)
            remember(entry, path.stem, lines.get(path.stem, 0) + 1)
            return True

    def verify() -> dict:
        """Walk every line in order: payload hash and link to the line before. The first file's first `prev` is
        taken as given (earlier months may have gone to cold storage)."""
        prev, checked = None, 0
        for path in files():
            for number, raw in enumerate(path.read_bytes().splitlines(), 1):
                checked += 1
                where = {"month": path.stem, "line": number}
                try:
                    entry = json.loads(raw)
                except ValueError:
                    return {"ok": False, "lines": checked, "broken": {**where, "reason": "Dòng không phải JSON."}}
                if not isinstance(entry, dict) or sha256(canonical(entry.get("payload"))) != entry.get("sha256"):
                    return {"ok": False, "lines": checked, "broken": {**where, "reason": "Nội dung hồ sơ đã bị sửa (sha256 không khớp)."}}
                if prev is not None and entry.get("prev") != prev:
                    return {"ok": False, "lines": checked, "broken": {**where, "reason": "Dòng trước nó đã bị sửa, xoá hoặc chèn (prev không khớp)."}}
                prev = sha256(raw)
        return {"ok": True, "lines": checked, "head": prev or GENESIS}

    def keep_months() -> int:
        try:
            return max(1, int(app.org_settings(DEFAULTS)["giu_thang"]))
        except (TypeError, ValueError):
            return DEFAULTS["giu_thang"]

    app.archive, app.verify, app.folder = archive, verify, folder

    @app.route("POST", "/events", signed=True)
    def events(request):
        body = request.json()
        kind, subject = body.get("type"), body.get("subject") or {}
        if kind == "plugin.settings.changed":
            app.forget_settings()
        if kind not in EVENTS or subject.get("type") != "case":
            return Response(202, b"{}")
        try:
            case = app.desktiny.case(subject["id"])
        except PluginError as exc:
            if exc.status >= 500:
                raise  # Desktiny retries a failed delivery; a missing or forbidden dossier is not retried
            return Response(202, b"{}")
        archive(body, case)
        return Response(202, b"{}")

    @app.route("GET", "/api/quan-tri", admin=True)
    def overview(request):
        keep = keep_months()
        cutoff = months_before(f"{now():%Y-%m}", keep)
        months = [{"month": m, "lines": n, "cold": m <= cutoff} for m, n in sorted(lines.items(), reverse=True)]
        return {"months": months, "keep_months": keep, "head": head["hash"], "total": sum(lines.values())}

    @app.route("POST", "/api/quan-tri/kiem", admin=True)
    def check(request):
        return verify()

    @app.route("GET", "/api/quan-tri/tim", admin=True)
    def search(request):
        code = str(request.query.get("ma") or "").strip().upper()
        if not code:
            raise HttpError(422, "Nhập mã hồ sơ, ví dụ HS-000123.", "invalid")
        return {"code": code, "items": by_code.get(code, [])}

    @app.route("GET", "/api/quan-tri/thang/{month}", admin=True)
    def export(request):
        month = request.params["month"]
        path = folder / f"{month}.jsonl"
        if not MONTH.match(month) or not path.is_file():
            raise HttpError(404, "Không có tệp lưu trữ của tháng này.", "not_found")
        # shortcut: the whole month goes into the page to copy (frames cannot download); fine for small months.
        return {"month": month, "text": path.read_text(encoding="utf-8")}

    return app


if __name__ == "__main__":
    build().run(9209)
