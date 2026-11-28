# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Play a device for the Cảm biến thiết bị plugin (demos): normal readings, a spike past the threshold, normal again.
With the default threshold (nhiet_do>80) that is one incident: one event, one incident dossier.

    python scripts/gia_lap_cam_bien.py --khoa <khoá thiết bị> [--url http://localhost:9208] [--thiet-bi lo-say-1]

The key is the one the plugin's admin page showed when the device was registered.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request


def readings(count: int, base: float, peak: float) -> list[float]:
    """`count` values around `base`, with three past `peak` in the middle."""
    values = [round(base + random.uniform(-3, 3), 1) for _ in range(count)]
    middle = count // 2
    for offset, extra in zip(range(-1, 2), (-3, 0, -1), strict=True):
        if 0 <= middle + offset < count:
            values[middle + offset] = peak + extra
    return values


def send(url: str, key: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url.rstrip("/") + "/api/so-do", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Device-Key": key})  # fmt: skip
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 (the operator's own plugin server)
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:9208", help="Máy chủ plugin Cảm biến thiết bị.")
    parser.add_argument("--khoa", required=True, help="Khoá thiết bị (X-Device-Key).")
    parser.add_argument("--thiet-bi", default="lo-say-1", help="Mã thiết bị đã đăng ký.")
    parser.add_argument("--chi-so", default="nhiet_do")
    parser.add_argument("--so-lan", type=int, default=10, help="Số lần gửi.")
    parser.add_argument("--nen", type=float, default=65, help="Giá trị bình thường.")
    parser.add_argument("--dinh", type=float, default=95, help="Giá trị đợt vượt ngưỡng.")
    parser.add_argument("--cach-giay", type=float, default=2, help="Khoảng cách giữa hai lần gửi (giây).")
    args = parser.parse_args()
    failed = 0
    for number, value in enumerate(readings(args.so_lan, args.nen, args.dinh), 1):
        if number > 1:
            time.sleep(args.cach_giay)
        try:
            status, data = send(args.url, args.khoa, {"thiet_bi": args.thiet_bi, "chi_so": args.chi_so, "gia_tri": value})
        except OSError as exc:
            print(f"✗ Không gửi được tới {args.url}: {exc}")
            return 2
        failed += status != 200
        state = {"opened": "mở sự cố → gửi sự kiện", "open": "sự cố đang mở", "closed": "trở lại bình thường"}.get(data.get("su_co"), "")
        print(f"{number:>3}. {args.chi_so} = {value:<6} → {status} {data.get('message', '')}{state}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
