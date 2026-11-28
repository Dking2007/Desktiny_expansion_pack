# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import hashlib
import json
from datetime import datetime, timezone

from conftest import call, load, signed

server = load("luu-tru-lich-su")


def dossier(case_id="c1", updated="2026-11-02T08:00:00Z", **payload):
    return {"id": case_id, "code": f"HS-{case_id.upper()}", "title": "Đăng ký khai sinh", "status": "approved",
            "form": {"id": "f-ks", "name": "Khai sinh"}, "updated_at": updated,
            "payload": {"ho_ten": "Nguyễn Văn An", "so_cccd": "001203004567", "dien_thoai": "0912 345 678",
                        "email": "an.nguyen@example.vn", **payload}}  # fmt: skip


def event(kind="case.approved", case_id="c1", event_id="e1"):
    return {"event_id": event_id, "type": kind, "occurred_at": "2026-11-02T08:00:01Z", "subject": {"type": "case", "id": case_id}}


def at(month: int):
    return lambda: datetime(2026, month, 15, 9, 0, tzinfo=timezone.utc)


def lines(app, month="2026-11") -> list[bytes]:
    return (app.folder / f"{month}.jsonl").read_bytes().splitlines()


def test_redact_masks_id_numbers_phones_and_emails_only():
    text = "CCCD 001203004567, CMND 123456789, ĐT 0912.345.678 hoặc +84 912345678, thư an@x.vn, sinh 05/03/1990"
    assert server.redact({"a": [text], "n": 5}) == {
        "a": ["CCCD [CCCD], CMND [CMND], ĐT [SĐT] hoặc [SĐT], thư [EMAIL], sinh 05/03/1990"], "n": 5}  # fmt: skip
    assert server.redact("mã 12345678901234") == "mã 12345678901234"  # longer runs of digits are left alone


def test_an_event_appends_a_redacted_line_chained_to_the_one_before(make_app, desktiny):
    app = make_app("luu-tru-lich-su", now=at(11))
    desktiny.cases = {"c1": dossier(), "c2": dossier("c2")}
    assert signed(app, "/events", event()).status == 202
    assert signed(app, "/events", event(case_id="c2", event_id="e2")).status == 202
    first, second = lines(app)
    entry = json.loads(first)
    assert entry["payload"] == {"ho_ten": "Nguyễn Văn An", "so_cccd": "[CCCD]", "dien_thoai": "[SĐT]", "email": "[EMAIL]"}
    assert "001203004567" not in first.decode() and "example.vn" not in first.decode()
    canonical = json.dumps(entry["payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert entry["sha256"] == hashlib.sha256(canonical).hexdigest() and entry["prev"] == "0" * 64
    assert (entry["case_id"], entry["code"], entry["form_id"], entry["version"], entry["event"]) == (
        "c1", "HS-C1", "f-ks", "2026-11-02T08:00:00Z", "case.approved")  # fmt: skip
    assert entry["occurred_at"] == "2026-11-02T08:00:01Z" and entry["archived_at"].startswith("2026-11-15")
    assert json.loads(second)["prev"] == hashlib.sha256(first).hexdigest()
    assert app.verify() == {"ok": True, "lines": 2, "head": hashlib.sha256(second).hexdigest()}


def test_replays_do_not_duplicate_but_a_new_version_or_event_does(make_app, desktiny):
    app = make_app("luu-tru-lich-su", now=at(11))
    desktiny.cases = {"c1": dossier()}
    signed(app, "/events", event())
    signed(app, "/events", event())  # Desktiny delivering the same event again
    signed(app, "/events", event(event_id="e-khac"))  # same dossier version, same kind of event
    assert len(lines(app)) == 1
    signed(app, "/events", event("case.closed", event_id="e2"))
    desktiny.cases["c1"] = dossier(updated="2026-11-20T10:00:00Z")
    signed(app, "/events", event(event_id="e3"))
    assert len(lines(app)) == 3
    # Restarting rebuilds the index from the files: still no duplicate, and the chain carries on.
    again = make_app("luu-tru-lich-su", now=at(12))
    signed(again, "/events", event(event_id="e3"))
    desktiny.cases["c2"] = dossier("c2")
    signed(again, "/events", event(case_id="c2", event_id="e4"))
    assert len(lines(again)) == 3 and len(lines(again, "2026-12")) == 1
    assert json.loads(lines(again, "2026-12")[0])["prev"] == hashlib.sha256(lines(again)[-1]).hexdigest()
    assert again.verify()["ok"] is True


def test_other_events_unsigned_calls_and_missing_dossiers_archive_nothing(make_app, desktiny):
    app = make_app("luu-tru-lich-su", now=at(11))
    desktiny.cases = {"c1": dossier()}
    assert signed(app, "/events", event("case.submitted")).status == 202
    assert signed(app, "/events", event(case_id="khong-co")).status == 202
    assert call(app, "POST", "/events", body=event()).status == 401
    assert not (app.folder / "2026-11.jsonl").exists()


def test_a_tampered_line_is_reported_at_the_first_break(make_app, desktiny, tmp_path):
    app = make_app("luu-tru-lich-su", now=at(11))
    desktiny.cases = {c: dossier(c) for c in ("c1", "c2", "c3")}
    for n, case_id in enumerate(("c1", "c2", "c3")):
        signed(app, "/events", event(case_id=case_id, event_id=f"e{n}"))
    path = app.folder / "2026-11.jsonl"
    original = path.read_bytes()
    path.write_bytes(original.replace(b"Nguy\xe1\xbb\x85n V\xc4\x83n An", b"Tr\xe1\xba\xa7n V\xc4\x83n B", 1))
    report = call(app, "POST", "/api/quan-tri/kiem", body={}, session="phien-qt").data
    assert report["ok"] is False and report["broken"]["month"] == "2026-11" and report["broken"]["line"] == 1
    # Editing a field outside the payload (and fixing its sha256 too) shows up at the next line's prev.
    rows = original.splitlines()
    second = json.loads(rows[1])
    second["code"] = "HS-GIA"
    rows[1] = json.dumps(second, ensure_ascii=False, separators=(",", ":")).encode()
    path.write_bytes(b"\n".join(rows) + b"\n")
    assert app.verify()["broken"]["line"] == 3
    # Deleting a line breaks the chain too.
    path.write_bytes(b"\n".join([original.splitlines()[0], original.splitlines()[2]]) + b"\n")
    assert app.verify()["broken"]["line"] == 2
    # A line cut short by a crash: the next one is written on its own line, and verify points at the cut one.
    path.write_bytes(original + b'{"case_id":"c4"')
    restarted = make_app("luu-tru-lich-su", now=at(11))
    desktiny.cases["c4"] = dossier("c4")
    signed(restarted, "/events", event(case_id="c4", event_id="e9"))
    assert json.loads(lines(restarted)[-1])["case_id"] == "c4" and len(lines(restarted)) == 5
    assert restarted.verify()["broken"] == {"month": "2026-11", "line": 4, "reason": "Dòng không phải JSON."}


def test_admin_routes_need_the_admin_page(make_app, desktiny):
    app = make_app("luu-tru-lich-su", now=at(11))
    for method, path in (("GET", "/api/quan-tri"), ("POST", "/api/quan-tri/kiem"), ("GET", "/api/quan-tri/tim?ma=HS-C1"),
                         ("GET", "/api/quan-tri/thang/2026-11")):  # fmt: skip
        assert call(app, method, path, body={} if method == "POST" else None, session="phien-an").status == 403
        assert call(app, method, path, body={} if method == "POST" else None).status == 401


def test_lineage_search_months_retention_and_export(make_app, desktiny):
    month = {"value": 1}
    app = make_app("luu-tru-lich-su", now=lambda: datetime(2026, month["value"], 10, tzinfo=timezone.utc))
    desktiny.cases = {"c1": dossier(updated="2026-01-09T00:00:00Z")}
    signed(app, "/events", event())
    month["value"] = 11
    desktiny.cases["c1"] = dossier(updated="2026-11-09T00:00:00Z")
    signed(app, "/events", event("case.closed", event_id="e2"))
    found = call(app, "GET", "/api/quan-tri/tim?ma=hs-c1", session="phien-qt").data
    assert [(i["month"], i["line"], i["event"], i["case_id"]) for i in found["items"]] == [
        ("2026-01", 1, "case.approved", "c1"), ("2026-11", 1, "case.closed", "c1")]  # fmt: skip
    assert call(app, "GET", "/api/quan-tri/tim?ma=HS-KHONG", session="phien-qt").data["items"] == []
    desktiny.settings = {"giu_thang": 6}
    data = call(app, "GET", "/api/quan-tri", session="phien-qt").data
    assert data["months"] == [{"month": "2026-11", "lines": 1, "cold": False}, {"month": "2026-01", "lines": 1, "cold": True}]
    assert data["keep_months"] == 6 and data["total"] == 2
    text = call(app, "GET", "/api/quan-tri/thang/2026-01", session="phien-qt").data["text"]
    assert json.loads(text)["version"] == "2026-01-09T00:00:00Z"
    assert call(app, "GET", "/api/quan-tri/thang/..", session="phien-qt").status == 404
    assert server.months_before("2026-01", 1) == "2025-12"
