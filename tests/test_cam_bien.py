# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Cảm biến thiết bị: device keys, readings, one event per incident, events kept while Desktiny is down."""

import hashlib
import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from conftest import FakeClient, call

from desktiny_plugin import PluginError

NOW = datetime(2026, 11, 28, 1, 0, tzinfo=timezone.utc)


@pytest.fixture
def app(make_app, desktiny):
    desktiny.settings = {"nguong": "nhiet_do>80; nhiet_do<5; do_am>90", "nguoi_phu_trach": "Trần Thị Bình", "luu_ngay": 30}
    return make_app("cam-bien", now=lambda: NOW)


def register(app, ma="lo-say-1", ten="Lò sấy số 1"):
    response = call(app, "POST", "/api/quan-tri/thiet-bi", {"ma": ma, "ten": ten, "vi_tri": "Xưởng A"}, session="phien-qt")
    assert response.status == 200, response.body
    return response.data["khoa"]


def post(app, key, **body):
    headers = {"Content-Type": "application/json", **({"X-Device-Key": key} if key else {})}
    return app.handle("POST", "/api/so-do", headers, json.dumps({"thiet_bi": "lo-say-1", "chi_so": "nhiet_do", **body}).encode())


def events(desktiny):
    return [c for c in desktiny.calls if c[0] == "send_event"]


def test_a_device_key_is_shown_once_kept_hashed_and_can_be_replaced(app):
    key = register(app)
    row = app.store.one("SELECT key_hash FROM devices WHERE id = 'lo-say-1'")
    assert row["key_hash"] == hashlib.sha256(key.encode()).hexdigest() and key not in json.dumps(row)
    assert call(app, "POST", "/api/quan-tri/thiet-bi", {"ma": "lo-say-1", "ten": "Trùng"}, session="phien-qt").status == 409
    assert call(app, "POST", "/api/quan-tri/thiet-bi", {"ma": "x", "ten": "Y"}, session="phien-an").status == 403  # not admin
    assert key not in json.dumps(call(app, "GET", "/api/quan-tri", session="phien-qt").data)
    fresh = call(app, "POST", "/api/quan-tri/thiet-bi/lo-say-1/khoa", session="phien-qt").data["khoa"]
    assert post(app, key, gia_tri=20).status == 403
    assert post(app, fresh, gia_tri=20).status == 200


def test_readings_need_the_device_key(app):
    key = register(app)
    assert post(app, None, gia_tri=20).status == 401
    assert post(app, "sai-khoa", gia_tri=20).status == 403
    assert post(app, key, gia_tri=20, thiet_bi="khong-co").status == 403
    assert app.store.one("SELECT COUNT(*) AS n FROM readings")["n"] == 0


def test_readings_are_checked_before_they_are_kept(app):
    key = register(app)
    assert post(app, key, chi_so="Nhiệt độ", gia_tri=20).status == 422
    for value in ("20", True, None, float("nan")):
        assert post(app, key, gia_tri=value).status == 422, value
    assert post(app, key, gia_tri=20, thoi_diem="hôm qua").status == 422
    assert post(app, key, gia_tri=20, thoi_diem="2026-11-28T08:00:00").status == 422  # no time zone
    assert post(app, key, gia_tri=20, thoi_diem="2026-11-29T08:00:00+07:00").status == 422  # in the future
    kept = post(app, key, gia_tri=21.5, thoi_diem="2026-11-28T07:30:00+07:00")
    assert kept.status == 200 and kept.data["thoi_diem"] == "2026-11-28T00:30:00+00:00"
    assert app.store.all("SELECT metric, value FROM readings") == [{"metric": "nhiet_do", "value": 21.5}]


def test_a_threshold_crossing_sends_one_event_until_the_value_is_back_to_normal(app, desktiny):
    key = register(app)
    states = [post(app, key, gia_tri=v).data["su_co"] for v in (70, 85, 90, 95)]
    assert states == [None, "opened", "open", "open"]
    (event,) = events(desktiny)
    assert event[2][0] == "canh_bao_cam_bien" and event[3]["key"] == "su-co:1"
    assert event[2][1] == {"thiet_bi": "lo-say-1", "ten_thiet_bi": "Lò sấy số 1", "vi_tri": "Xưởng A", "chi_so": "nhiet_do",
                           "gia_tri": 85.0, "nguong": "> 80", "thoi_diem": "2026-11-28T01:00:00+00:00",
                           "nguoi_phu_trach": "Trần Thị Bình"}  # fmt: skip
    assert post(app, key, gia_tri=60).data["su_co"] == "closed"
    assert post(app, key, gia_tri=3).data["su_co"] == "opened"  # the low threshold is an incident of its own
    assert [e[2][1]["nguong"] for e in events(desktiny)] == ["> 80", "< 5"]
    # Another metric, or a metric without a threshold, does not touch the incident.
    assert post(app, key, chi_so="ap_suat", gia_tri=999).data["su_co"] is None
    assert len(events(desktiny)) == 2


def test_events_wait_while_desktiny_is_down_and_go_out_later(app, desktiny, monkeypatch):
    key = register(app)
    sent = FakeClient.send_event

    def down(self, *args, **kwargs):
        raise OSError("Connection refused")

    monkeypatch.setattr(FakeClient, "send_event", down)
    assert post(app, key, gia_tri=99).status == 200  # the device is answered all the same
    assert post(app, key, gia_tri=40, chi_so="do_am").status == 200
    assert post(app, key, gia_tri=95, chi_so="do_am").status == 200
    assert call(app, "GET", "/api/quan-tri", session="phien-qt").data["pending"] == 2
    assert app.round()["sent"] == 0  # still down: nothing lost

    def stale_token(self, *args, **kwargs):
        raise PluginError(401, "plugin_token_invalid", "x")

    monkeypatch.setattr(FakeClient, "send_event", stale_token)
    assert app.round()["sent"] == 0  # a token being replaced is not a refusal of the events
    monkeypatch.setattr(FakeClient, "send_event", sent)
    assert app.round()["sent"] == 2
    assert [e[3]["key"] for e in events(desktiny)] == ["su-co:1", "su-co:2"]
    assert app.store.one("SELECT COUNT(*) AS n FROM outbox")["n"] == 0


def test_an_event_desktiny_refuses_for_good_does_not_hold_up_the_others(app, desktiny, monkeypatch):
    key = register(app)
    sent = FakeClient.send_event

    def refuse(self, event_type, data=None, key=None):
        if data["chi_so"] == "nhiet_do":
            raise PluginError(422, "plugin_event_invalid", "sai")
        return sent(self, event_type, data, key)

    monkeypatch.setattr(FakeClient, "send_event", refuse)
    post(app, key, gia_tri=99)
    post(app, key, chi_so="do_am", gia_tri=99)
    assert [e[2][1]["chi_so"] for e in events(desktiny)] == ["do_am"]
    failed = call(app, "GET", "/api/quan-tri", session="phien-qt").data["failed"]
    assert [f["key"] for f in failed] == ["su-co:1"] and "422" in failed[0]["error"]


def test_a_device_sending_too_often_is_slowed_down(app):
    key = register(app)
    other = register(app, "kho-lanh", "Kho lạnh")
    answers = [post(app, key, gia_tri=20).status for _ in range(31)]
    assert answers[:30] == [200] * 30 and answers[30] == 429
    assert post(app, other, thiet_bi="kho-lanh", gia_tri=20).status == 200


def test_old_readings_and_closed_incidents_are_dropped(app):
    key = register(app)
    old = (NOW - timedelta(days=40)).isoformat()
    post(app, key, gia_tri=90, thoi_diem=old)
    post(app, key, gia_tri=20, thoi_diem=old)
    post(app, key, gia_tri=22)
    app.round()
    assert [r["value"] for r in app.store.all("SELECT value FROM readings")] == [22.0]
    assert app.store.one("SELECT COUNT(*) AS n FROM incidents")["n"] == 0


def test_the_simulator_over_http_makes_exactly_one_incident(app, desktiny):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import gia_lap_cam_bien

    key = register(app)
    server = app.server(0, "127.0.0.1")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        states = [gia_lap_cam_bien.send(url, key, {"thiet_bi": "lo-say-1", "chi_so": "nhiet_do", "gia_tri": v})
                  for v in gia_lap_cam_bien.readings(10, 65, 95)]  # fmt: skip
        assert gia_lap_cam_bien.send(url, "sai", {"thiet_bi": "lo-say-1", "chi_so": "nhiet_do", "gia_tri": 1})[0] == 403
    finally:
        server.shutdown()
        server.server_close()
    assert [status for status, _ in states] == [200] * 10
    assert [data["su_co"] for _, data in states if data["su_co"]] == ["opened", "open", "open", "closed"]
    assert len(events(desktiny)) == 1


def test_the_home_block_shows_the_latest_readings_and_open_incidents(app):
    key = register(app)
    for value in (70, 75, 85):
        post(app, key, gia_tri=value)
    post(app, key, chi_so="do_am", gia_tri=55)
    assert call(app, "GET", "/api/tong-quan").status == 401  # needs a Desktiny session
    (device,) = call(app, "GET", "/api/tong-quan", session="phien-an").data["items"]
    metrics = {m["metric"]: m for m in device["metrics"]}
    assert metrics["nhiet_do"]["value"] == 85 and metrics["nhiet_do"]["series"] == [70, 75, 85]
    assert metrics["nhiet_do"]["alert"] is True and metrics["do_am"]["alert"] is False
    assert metrics["nhiet_do"]["limits"] == ["> 80", "< 5"]
