// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Small pieces the Sổ văn bản pages share: the register number as type, dates read from the stored ISO time
// (Vietnam time, so no time-zone shifting), a document sheet with its heading and the stamp that lands on it.
import { h } from './mo-rong.js'
import { docHead, seal } from './bieu-do.js'

/** "12/QĐ-UBND" with the numeral set heavier than the symbol. */
export function numberMark(full, { big = false, cancelled = false } = {}) {
  const [, numeral, tail] = String(full ?? '').match(/^(\d+)(.*)$/) || [null, String(full ?? ''), '']
  const classes = ['sv-no', big ? 'is-big' : '', cancelled ? 'is-cancelled' : ''].filter(Boolean).join(' ')
  return h('span', { class: classes, 'aria-label': cancelled ? `${full}, đã huỷ` : null }, h('b', {}, numeral), tail ? h('span', {}, tail) : null)
}

/** '2026-11-26T09:15:00+07:00' → '26/11/2026'. */
export const dayOf = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
/** '2026-11-26T09:15:00+07:00' → '09:15'. */
export const timeOf = (iso) => iso.slice(11, 16)

/** Today's date (viewer's clock) as 'YYYY-MM-DD'. */
export function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** The agency line of a document heading: its configured name, else its symbol. */
export function agencyName(agency) {
  return agency?.name || agency?.symbol || 'Cơ quan ban hành'
}

/**
 * A document sheet: Nghị định 30 heading, the document type as title, the summary, placeholder body lines and a
 * place for the stamp. `number` may be a node (to mark a preview).
 */
export function docSheet({ agency, number, date, kind, summary, label }) {
  const head = docHead({ agency: agencyName(agency), number: typeof number === 'string' ? number : '', place: agency?.place || '', date })
  if (number instanceof Node) {
    const no = head.querySelector('.gd-doc-agency')
    no.append(h('div', { class: 'gd-doc-no' }, 'Số: ', number))
  }
  const stampSpot = h('div', { class: 'sv-stamp-spot', style: 'position:absolute;right:22px;bottom:18px' })
  return h(
    'article',
    { class: 'gd-doc', 'aria-label': label || 'Văn bản' },
    head,
    h('div', { class: 'gd-doc-title' }, String(kind || 'Văn bản').toLocaleUpperCase('vi')),
    summary ? h('p', { class: 'gd-doc-summary' }, summary) : null,
    h('div', { class: 'sv-lines', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'), h('i')),
    stampSpot,
  )
}

/** Put a stamp on a sheet made by docSheet, landing it with the one short motion. */
export function stamp(sheet, text, sub, tone = '') {
  const mark = seal(text, sub, tone)
  mark.classList.add('sv-landing')
  sheet.querySelector('.sv-stamp-spot').replaceChildren(mark)
  return mark
}

/** A small document thumbnail for a list row; a cancelled number carries a "Huỷ" stamp. */
export function thumb(symbol, cancelled = false) {
  return h(
    'span',
    { class: 'sv-thumb', 'aria-hidden': 'true' },
    h('span', {}, symbol || 'VB'),
    h('i'),
    h('i'),
    h('i'),
    cancelled ? seal('Huỷ') : null,
  )
}
