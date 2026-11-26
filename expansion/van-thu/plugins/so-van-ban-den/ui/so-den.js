// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Shared by the register's pages: how an entry's standing reads and looks, dates read from the stored ISO time
// (Vietnam time, so no time-zone shifting), the "ĐẾN" stamp a clerk puts on an incoming document and the
// document sheet it lands on. Text is always set as text, never as HTML.
import { h } from './mo-rong.js'
import { chip, docHead, leaf, s } from './bieu-do.js'

export const STATUS = { open: 'Đang xử lý', due_soon: 'Sắp đến hạn', overdue: 'Quá hạn', done: 'Đã xử lý', cancelled: 'Đã huỷ số' }
const TONE = { open: 'accent', due_soon: 'warn', overdue: 'bad', done: 'ok', cancelled: 'muted' }
export const URGENT = new Set(['Khẩn', 'Thượng khẩn', 'Hoả tốc', 'Hỏa tốc'])

/** 2026-11-24 or an ISO time → 24/11/2026. */
export function day(value) {
  const [y, m, d] = String(value || '').slice(0, 10).split('-')
  return d ? `${d}/${m}/${y}` : ''
}

/** A date as the form may hold it ('2026-11-24', '24/11/2026', '24-11-2026') → '2026-11-24', or '' if unreadable. */
export function isoDate(value) {
  const text = String(value || '').trim()
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10)
  const found = text.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/)
  return found ? `${found[3]}-${found[2].padStart(2, '0')}-${found[1].padStart(2, '0')}` : ''
}

/** '2026-11-26T09:15:00+07:00' → '09:15'. */
export const timeOf = (iso) => String(iso || '').slice(11, 16)

/** Days left in words: "còn 3 ngày", "hạn hôm nay", "quá 2 ngày". */
export function countdown(days) {
  if (days === null || days === undefined) return ''
  return days < 0 ? `quá ${-days} ngày` : days === 0 ? 'hạn hôm nay' : days === 1 ? 'hạn ngày mai' : `còn ${days} ngày`
}

/** What the deadline means today for an entry, in words ('' once it is done or cancelled). */
export function left(entry) {
  if (entry.status === 'done' || entry.status === 'cancelled') return ''
  return countdown(entry.left)
}

export function toneOf(status) {
  return TONE[status] || 'muted'
}

/** The entry's standing as a chip, with the days left while it is open: "Quá hạn, quá 2 ngày". */
export function badge(entry, { days = true } = {}) {
  const extra = days ? left(entry) : ''
  return chip(extra && entry.status !== 'open' ? `${STATUS[entry.status]}, ${extra}` : STATUS[entry.status] ?? entry.status, toneOf(entry.status), entry.status === 'overdue' ? 'alert' : entry.status === 'done' ? 'check' : null)
}

/** A calendar leaf for a deadline, red once passed and amber while due soon; a blank leaf without one. */
export function dueLeaf(due, status) {
  if (!due) return h('span', { class: 'gd-leaf sd-leaf-blank', 'aria-hidden': 'true' }, h('b', {}, 'Hạn'), h('span', {}, '–'))
  return leaf(due, status === 'overdue' ? 'bad' : status === 'due_soon' ? 'warn' : status === 'done' || status === 'cancelled' ? 'muted' : 'accent')
}

/** The kit has no magnifier; drawn here in its line style. */
export function searchIcon() {
  return s('svg', { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.9, 'stroke-linecap': 'round', 'aria-hidden': 'true', class: 'gd-svg-icon' },
    s('circle', { cx: 11, cy: 11, r: 6.5 }), s('path', { d: 'M16 16l4.5 4.5' }))
}

/**
 * The "ĐẾN" stamp of the incoming-documents register (Nghị định 30, Phụ lục): a red rectangular stamp with the
 * lines Số, Ngày, Chuyển and Lưu hồ sơ số, filled in as by the clerk's pen. Generic: never an emblem or a seal.
 *   stampDen({ number, date, time, to, pending, cancelled, compact })
 * `pending` draws it as a preview (dashed, the number marked "dự kiến"); an empty value leaves a dotted blank.
 */
export function stampDen({ number, date, time, to, file, pending = false, cancelled = false, compact = false } = {}) {
  const blank = () => h('i', { class: 'sd-blank', 'aria-hidden': 'true' })
  const value = (text, cls = '') => (text ? h('b', { class: `sd-pen ${cls}`.trim() }, text) : blank())
  const label = [
    pending ? 'Bản xem trước dấu đến' : 'Dấu đến',
    number ? `số ${number}${pending ? ' (dự kiến)' : ''}${cancelled ? ', đã huỷ' : ''}` : 'chưa có số',
    date ? `ngày ${day(date)}${time ? ' lúc ' + time : ''}` : '',
    to ? `chuyển ${to}` : '',
  ].filter(Boolean).join(', ')
  const classes = ['sd-stamp', pending ? 'is-pending' : '', cancelled ? 'is-cancelled' : '', compact ? 'is-compact' : ''].filter(Boolean).join(' ')
  return h(
    'div',
    { class: classes, role: 'img', 'aria-label': label },
    h('div', { class: 'sd-stamp-in', 'aria-hidden': 'true' },
      h('span', { class: 'sd-stamp-word' }, 'ĐẾN'),
      h('span', { class: 'sd-stamp-line sd-line-no' }, h('span', {}, 'Số:'), number ? h('b', { class: 'sd-pen sd-stamp-no' }, number) : blank(), pending && number ? h('small', { class: 'sd-pending-tag' }, 'dự kiến') : null),
      h('span', { class: 'sd-stamp-line' }, h('span', {}, 'Ngày:'), value(date ? day(date) : '', 'sd-date'), time ? h('small', { class: 'sd-pen sd-time' }, time) : null),
      h('span', { class: 'sd-stamp-line sd-wide' }, h('span', {}, 'Chuyển:'), value(to)),
      h('span', { class: 'sd-stamp-line sd-wide' }, h('span', {}, 'Lưu hồ sơ số:'), value(file)),
    ),
  )
}

/** Land a stamp: the one short motion that answers registering. giao-dien.css turns it off for reduced motion. */
export function land(stamp) {
  stamp.classList.add('is-landing')
  return stamp
}

/**
 * The incoming document as a sheet: its sender's heading (Nghị định 30 layout), the document type and summary,
 * placeholder body lines, and a place on the left under the heading where the "ĐẾN" stamp goes.
 */
export function docSheet(draft, stamp) {
  const kind = draft.loai_van_ban && draft.loai_van_ban !== 'Khác' ? draft.loai_van_ban : ''
  const isLetter = !kind || kind === 'Công văn'
  const head = docHead({ agency: draft.noi_gui || 'Cơ quan gửi', number: draft.so_ky_hieu_goc || '', date: isoDate(draft.ngay_van_ban) || null })
  if (isLetter && draft.trich_yeu) head.querySelector('.gd-doc-agency').append(h('div', { class: 'sd-doc-vv' }, `V/v ${draft.trich_yeu.replace(/^v(ề|e) việc\s+/i, '')}`))
  return h(
    'article',
    { class: 'gd-doc sd-doc', 'aria-label': `Văn bản đến của ${draft.noi_gui || 'cơ quan gửi'}${draft.so_ky_hieu_goc ? ', số ' + draft.so_ky_hieu_goc : ''}` },
    head,
    URGENT.has(draft.do_khan) ? h('span', { class: 'sd-urgency' }, draft.do_khan.toLocaleUpperCase('vi')) : null,
    !isLetter ? h('div', { class: 'gd-doc-title' }, kind.toLocaleUpperCase('vi')) : null,
    !isLetter && draft.trich_yeu ? h('p', { class: 'gd-doc-summary' }, draft.trich_yeu) : null,
    h('div', { class: 'sd-doc-body' }, h('div', { class: 'sd-stamp-spot' }, stamp), h('div', { class: 'sd-lines', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'), h('i'), h('i'))),
  )
}
