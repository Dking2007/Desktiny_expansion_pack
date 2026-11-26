// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { PRESETS, addWorkingDays, dayKind, dueDetails, holidayName, iso, parseDayList, timeLimitFor, workingDaysBetween } from '../../expansion/mot-cua-xa/plugins/tinh-han/ui/ngay-lam-viec.js'

test('weekends and holidays are skipped, moved workdays count', () => {
  // Friday 24/04/2026 + 1 working day: Monday 27/04 is the Hùng Kings day off, so Tuesday 28/04.
  assert.equal(iso(addWorkingDays('2026-04-24', 1)), '2026-04-28')
  // 29/04 + 1: 30/04 and 01/05 off, weekend, so Monday 04/05.
  assert.equal(iso(addWorkingDays('2026-04-29', 1)), '2026-05-04')
  assert.equal(iso(addWorkingDays('2026-11-13', 5)), '2026-11-20')
  // Received on a Saturday, "the same day" means the next working day.
  assert.equal(iso(addWorkingDays('2026-11-14', 0)), '2026-11-16')
  const saturday = new Set(['2026-11-14'])
  assert.equal(iso(addWorkingDays('2026-11-13', 1, new Set(), saturday)), '2026-11-14')
})

test('working days between two dates, and usual limits by procedure', () => {
  assert.equal(workingDaysBetween('2026-11-13', '2026-11-20'), 5)
  assert.equal(workingDaysBetween('2026-11-20', '2026-11-13'), -5)
  assert.equal(timeLimitFor('Đăng ký khai sinh'), 0)
  assert.equal(timeLimitFor('Xác nhận tình trạng hôn nhân'), 3)
  assert.equal(timeLimitFor('Bất kỳ', { so_ngay_giai_quyet: 12 }), 12)
  assert.equal(timeLimitFor('Bất kỳ'), 5)
})

test('the way to the deadline: counted days in order, skipped days with why', () => {
  const way = dueDetails('2026-04-24', 3)
  assert.equal(way.due, iso(addWorkingDays('2026-04-24', 3)))
  assert.deepEqual(way.counted, ['2026-04-28', '2026-04-29', '2026-05-04'])
  assert.deepEqual(way.skipped.map((s) => s.kind), ['weekend', 'weekend', 'holiday', 'holiday', 'holiday', 'weekend', 'weekend'])
  assert.equal(way.calendarDays, 10)
  assert.deepEqual(dueDetails('2026-11-14', 0), { from: '2026-11-14', due: '2026-11-16', counted: [], skipped: [{ day: '2026-11-14', kind: 'weekend' }, { day: '2026-11-15', kind: 'weekend' }], calendarDays: 2 })
  assert.equal(dayKind('2026-11-14', new Set(), new Set(['2026-11-14'])), 'moved')
  assert.equal(holidayName('2026-09-02'), 'Quốc khánh')
  assert.equal(holidayName('2027-04-30'), 'Ngày Giải phóng miền Nam')
  assert.equal(holidayName('2026-11-20'), '')
})

test('day lists typed one per line, with an optional name', () => {
  const { days, names } = parseDayList('2026-09-02 Quốc khánh\r\nghi chú\n2026-02-30\n 2026-12-31')
  assert.deepEqual([...days], ['2026-09-02', '2026-12-31'])
  assert.deepEqual(names, { '2026-09-02': 'Quốc khánh' })
  assert.equal(PRESETS.every((p) => Number.isInteger(p.days) && p.label), true)
})
