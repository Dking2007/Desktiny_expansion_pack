// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Working days: skip Saturdays, Sundays and public holidays; a day the government moves work to counts.
// Dates are "YYYY-MM-DD" strings, computed in UTC so no timezone shifts a day.

/**
 * Public holidays (and days off moved next to them) for state offices. Lunar holidays move every year:
 * check the government's yearly announcement and edit this list before packing the plugin.
 */
export const HOLIDAYS = {
  2026: [
    '2026-01-01',
    // Tết Nguyên đán Bính Ngọ (mùng 1 Tết: 17/02/2026)
    '2026-02-16', '2026-02-17', '2026-02-18', '2026-02-19', '2026-02-20',
    // Giỗ Tổ Hùng Vương (10/3 âm lịch: 26/04/2026, Chủ nhật) nghỉ bù thứ Hai
    '2026-04-27',
    '2026-04-30', '2026-05-01',
    '2026-09-01', '2026-09-02',
  ],
  2027: ['2027-01-01', '2027-04-30', '2027-05-01', '2027-09-02'],
}
/** Saturdays or Sundays worked in place of a day off (none listed by default). */
export const WORKDAYS = []

export function parseDay(text) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(text || ''))
  if (!match) return null
  const date = new Date(Date.UTC(+match[1], +match[2] - 1, +match[3]))
  return Number.isNaN(date.getTime()) ? null : date
}
export const iso = (date) => date.toISOString().slice(0, 10)

export function isWorkingDay(date, holidays = new Set(Object.values(HOLIDAYS).flat()), workdays = new Set(WORKDAYS)) {
  const day = iso(date)
  if (workdays.has(day)) return true
  const weekday = date.getUTCDay()
  return weekday !== 0 && weekday !== 6 && !holidays.has(day)
}

/**
 * The deadline `days` working days after `from` (the day of receipt is not counted). Zero days means
 * "the same day" — or the next working day when received on a day off.
 */
export function addWorkingDays(from, days, holidays, workdays) {
  const date = typeof from === 'string' ? parseDay(from) : new Date(from.getTime())
  if (!date) throw new Error('Ngày không hợp lệ.')
  if (days <= 0) {
    while (!isWorkingDay(date, holidays, workdays)) date.setUTCDate(date.getUTCDate() + 1)
    return date
  }
  let left = days
  while (left > 0) {
    date.setUTCDate(date.getUTCDate() + 1)
    if (isWorkingDay(date, holidays, workdays)) left -= 1
  }
  return date
}

/** Working days from `from` (exclusive) to `to` (inclusive); negative when `to` is earlier. */
export function workingDaysBetween(from, to, holidays, workdays) {
  const start = typeof from === 'string' ? parseDay(from) : new Date(from.getTime())
  const end = typeof to === 'string' ? parseDay(to) : new Date(to.getTime())
  const sign = end >= start ? 1 : -1
  let count = 0
  const date = new Date(start.getTime())
  while (iso(date) !== iso(end)) {
    date.setUTCDate(date.getUTCDate() + sign)
    if (isWorkingDay(date, holidays, workdays)) count += sign
  }
  return count
}

/** Usual time limits (working days) by procedure name; a form field `so_ngay_giai_quyet` wins over these. */
export const TIME_LIMITS = [
  [/khai sinh|khai tử|kết hôn|chứng thực/i, 0],
  [/tình trạng hôn nhân/i, 3],
  [/hoà giải|hòa giải/i, 15],
  [/nghỉ phép|làm thêm|điều chỉnh công/i, 2],
]

export function timeLimitFor(title, payload = {}) {
  const field = Number(payload.so_ngay_giai_quyet)
  if (Number.isFinite(field) && field >= 0 && payload.so_ngay_giai_quyet !== '' && payload.so_ngay_giai_quyet != null) return field
  for (const [pattern, days] of TIME_LIMITS) if (pattern.test(title || '')) return days
  return 5
}
