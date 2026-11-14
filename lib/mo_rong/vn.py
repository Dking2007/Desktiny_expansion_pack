# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Small Vietnamese helpers shared by the plugins: dates, money, months."""

from __future__ import annotations

import re
from datetime import date, datetime


def month_of(value: str | None = None) -> str:
    """"2026-11" from "2026-11", "11/2026" or today."""
    if not value:
        return date.today().strftime("%Y-%m")
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value
    found = re.fullmatch(r"(\d{1,2})[/-](\d{4})", value)
    if found:
        return f"{found.group(2)}-{int(found.group(1)):02d}"
    raise ValueError("Tháng dạng 2026-11 hoặc 11/2026.")


def parse_date(value) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def money(value: float) -> str:
    """12.345.678 đ"""
    return f"{round(value):,}".replace(",", ".") + " đ"
