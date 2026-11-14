# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
from datetime import datetime, timedelta, timezone

from conftest import call, signed

VN = timezone(timedelta(hours=7))
OFFICE = {"name": "Trụ sở", "lat": 21.0285, "lng": 105.8542, "radius_m": 150}


def test_check_in_only_at_the_office_and_lateness_is_counted_and_announced(make_app, desktiny):
    clock = {"now": datetime(2026, 11, 2, 8, 20, tzinfo=VN)}
    app = make_app("cham-cong", now=lambda: clock["now"])
    desktiny.settings = {"nguong_di_muon": 2}
    # Only the plugin's admin page manages shifts and places.
    assert call(app, "POST", "/api/ca", {"name": "HC", "start": "08:00", "end": "17:00"}, "phien-an").status == 403
    assert call(app, "POST", "/api/ca", {"name": "Hành chính", "start": "08:00", "end": "17:00", "grace_minutes": 5},
                "phien-qt").status == 200  # fmt: skip
    assert call(app, "POST", "/api/dia-diem", OFFICE, "phien-qt").status == 200
    far = call(app, "POST", "/api/cham", {"kind": "in", "lat": 21.04, "lng": 105.86, "accuracy": 10}, "phien-an")
    assert far.status == 422 and "ngoài phạm vi" in far.data["message"]
    vague = call(app, "POST", "/api/cham", {"kind": "in", "lat": 21.0285, "lng": 105.8542, "accuracy": 500}, "phien-an")
    assert vague.status == 422
    assert call(app, "POST", "/api/cham", {"kind": "in", "lat": 21.0285, "lng": 105.8542}).status == 401
    first = call(app, "POST", "/api/cham", {"kind": "in", "lat": 21.0286, "lng": 105.8543, "accuracy": 12}, "phien-an")
    assert first.status == 200 and first.data["late_minutes"] == 15
    assert call(app, "POST", "/api/cham", {"kind": "in", "lat": 21.0286, "lng": 105.8543}, "phien-an").status == 409
    clock["now"] = datetime(2026, 11, 2, 16, 30, tzinfo=VN)
    left = call(app, "POST", "/api/cham", {"kind": "out", "lat": 21.0286, "lng": 105.8543}, "phien-an")
    assert left.data["late_minutes"] == -30  # left half an hour early
    assert not [c for c in desktiny.calls if c[0] == "send_event"]  # once is under the threshold
    clock["now"] = datetime(2026, 11, 3, 8, 10, tzinfo=VN)
    call(app, "POST", "/api/cham", {"kind": "in", "lat": 21.0286, "lng": 105.8543}, "phien-an")
    events = [c for c in desktiny.calls if c[0] == "send_event"]
    assert events[0][2] == ("di_muon", {"nhan_vien": "u-an", "so_lan": 2, "thang": "2026-11"})
    mine = call(app, "GET", "/api/toi?thang=2026-11", session="phien-an").data
    assert mine["summary"]["late_count"] == 2 and mine["summary"]["worked_days"] == 2 and mine["summary"]["hours"] == 8.17
    tool = signed(app, "/tools/di-muon", {"tool": "so_lan_di_muon", "arguments": {"thang": "11/2026"},
                                         "user": {"id": "u-an", "display_name": "An"}})  # fmt: skip
    assert tool.data["result"]["so_lan_di_muon"] == 2
    assert app.handle("POST", "/tools/di-muon", {}, b"{}").status == 401  # unsigned
    csv = call(app, "GET", "/api/xuat?thang=2026-11", session="phien-qt")
    assert csv.content_type.startswith("text/csv") and "Nguyễn Văn An,2,2,20,1,8.17" in csv.body.decode()


def test_payroll_reads_attendance_only_with_the_shared_key(make_app, desktiny):
    app = make_app("cham-cong")
    assert app.handle("GET", "/share/cong?thang=2026-11", {"X-Share-Key": "x"}).status == 401
    desktiny.settings = {"khoa_chia_se": "bi-mat-chung"}
    app.forget_settings()
    shared = app.handle("GET", "/share/cong?thang=2026-11", {"X-Share-Key": "bi-mat-chung"})
    assert shared.status == 200 and shared.data["items"] == []
    assign = call(app, "POST", "/api/phan-ca", {"department_id": "d1", "shift_id": None}, "phien-qt")
    assert assign.data["assigned"] == 3
