// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { addWorkingDays, iso, timeLimitFor, workingDaysBetween } from '../../plugins/tinh-han/ui/ngay-lam-viec.js'

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
