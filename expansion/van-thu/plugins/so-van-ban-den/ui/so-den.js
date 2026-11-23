// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Shared by the register's pages: how an entry's standing reads and looks.
import { h } from './mo-rong.js'

export const STATUS = { open: 'Đang xử lý', due_soon: 'Sắp đến hạn', overdue: 'Quá hạn', done: 'Đã xử lý', cancelled: 'Đã huỷ số' }

/** 2026-11-24 or an ISO time → 24/11/2026. */
export function day(value) {
  const [y, m, d] = String(value || '').slice(0, 10).split('-')
  return d ? `${d}/${m}/${y}` : ''
}

/** What the deadline means today, in words: "còn 3 ngày", "hôm nay", "quá 2 ngày". */
export function left(entry) {
  if (entry.left === null || entry.left === undefined || entry.status === 'done' || entry.status === 'cancelled') return ''
  return entry.left < 0 ? `quá ${-entry.left} ngày` : entry.left === 0 ? 'hạn hôm nay' : `còn ${entry.left} ngày`
}

export function badge(entry) {
  const tone = entry.status === 'overdue' ? 'bad' : entry.status === 'done' ? 'ok' : entry.status === 'due_soon' ? 'warn' : ''
  const extra = left(entry)
  return h('span', { class: `tag ${tone}` }, STATUS[entry.status] ?? entry.status, extra ? ` · ${extra}` : '')
}
