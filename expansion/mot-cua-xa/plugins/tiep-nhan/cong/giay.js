// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Helpers for the two public pages. They are not in a Desktiny frame, so they do not load the frame SDK (through
// mo-rong.js / bieu-do.js it would post messages to the page's parent); these build the same markup as the kit's
// seal(), leaf(), docHead() and icon(), styled by ../ui/giao-dien.css. Text is always set as text, never as HTML.

export const $ = (selector, root = document) => root.querySelector(selector)

/** Build an element: h('p', { class: 'x', onclick }, 'text', child). */
export function h(tag, attributes = {}, ...children) {
  const element = document.createElement(tag)
  for (const [key, value] of Object.entries(attributes || {})) {
    if (value === false || value === null || value === undefined) continue
    if (key.startsWith('on')) element.addEventListener(key.slice(2), value)
    else element.setAttribute(key, value === true ? '' : String(value))
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue
    element.append(child instanceof Node ? child : document.createTextNode(String(child)))
  }
  return element
}

const SVG = 'http://www.w3.org/2000/svg'
const ICONS = {
  clock: ['M12 7v5l3 2', 'circle:12,12,9'],
  calendar: ['M4 6h16v14H4z', 'M4 10h16', 'M8 3v4', 'M16 3v4'],
  alert: ['M12 3 2 20h20L12 3z', 'M12 10v4', 'M12 17.5v.5'],
  check: ['M5 12.5 10 17 19 7'],
  file: ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 12h6', 'M9 16h6'],
  lock: ['M6 11h12v9H6z', 'M8.5 11V8a3.5 3.5 0 0 1 7 0v3'],
  copy: ['M9 9h11v11H9z', 'M5 15H4V4h11v1'],
  print: ['M7 9V3h10v6', 'M7 17H4v-7h16v7h-3', 'M7 14h10v7H7z'],
  search: ['circle:11,11,7', 'M20 20l-4-4'],
  phone: ['M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2z'],
  chevronLeft: ['M15 6l-6 6 6 6'],
  chevronRight: ['M9 6l6 6-6 6'],
  edit: ['M4 20h4L19 9l-4-4L4 16v4z', 'M13.5 6.5l4 4'],
}

/** An inline line icon, decorative (hidden from screen readers). */
export function icon(name, size = 16) {
  const svg = document.createElementNS(SVG, 'svg')
  const attrs = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.9, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', class: 'gd-svg-icon' }
  for (const [key, value] of Object.entries(attrs)) svg.setAttribute(key, String(value))
  for (const part of ICONS[name] || []) {
    const shape = document.createElementNS(SVG, part.startsWith('circle:') ? 'circle' : 'path')
    if (part.startsWith('circle:')) {
      const [cx, cy, r] = part.slice(7).split(',')
      Object.entries({ cx, cy, r }).forEach(([k, v]) => shape.setAttribute(k, v))
    } else shape.setAttribute('d', part)
    svg.append(shape)
  }
  return svg
}

const WEEKDAYS = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy']

/** 'YYYY-MM-DD…' (or a Date) as a local calendar day. */
export function dayOf(value) {
  if (value instanceof Date) return value
  const [y, m, d] = String(value).slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}
const pad = (n) => String(n).padStart(2, '0')
/** 30/11/2026 */
export const dmy = (value) => {
  const date = dayOf(value)
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`
}
/** Thứ hai, 30/11/2026 */
export const longDay = (value) => `${WEEKDAYS[dayOf(value).getDay()]}, ${dmy(value)}`
/** 09:12, 26/11/2026 from an ISO time stamp (the server's clock, already in Vietnam time). */
export const stampText = (value) => `${String(value).slice(11, 16)}, ${dmy(value)}`

/** Days from today to a date (negative: already past). */
export function daysUntil(value) {
  const now = new Date()
  return Math.round((dayOf(value) - new Date(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000)
}

/** The kit's calendar leaf: month on top, day below. */
export function leaf(value, tone = 'muted') {
  const date = dayOf(value)
  return h('span', { class: `gd-leaf tone-${tone}`, 'aria-hidden': 'true' }, h('b', {}, `Th${date.getMonth() + 1}`), h('span', {}, date.getDate()))
}

/** The kit's ink stamp showing a state (never an emblem or a real seal). */
export function seal(text, sub = '', tone = '') {
  return h('span', { class: `gd-seal${tone ? ' tone-' + tone : ''}`, role: 'img', 'aria-label': sub ? `${text}, ${sub}` : text }, h('span', { 'aria-hidden': 'true' }, text, sub ? h('small', {}, sub) : null))
}

/** The kit's document heading (Nghị định 30): agency and number left, national title and date right. */
export function docHead({ agency = '', number = '', place = '', date } = {}) {
  const when = date ? dayOf(date) : null
  return h(
    'div',
    { class: 'gd-doc-head' },
    h('div', { class: 'gd-doc-agency' }, h('strong', {}, agency.toLocaleUpperCase('vi')), number ? h('div', { class: 'gd-doc-no' }, `Số: ${number}`) : null),
    h(
      'div',
      { class: 'gd-doc-nation' },
      h('strong', {}, 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'),
      h('span', {}, 'Độc lập - Tự do - Hạnh phúc'),
      when ? h('div', { class: 'gd-doc-date' }, `${place ? place + ', ' : ''}ngày ${when.getDate()} tháng ${when.getMonth() + 1} năm ${when.getFullYear()}`) : null,
    ),
  )
}

/**
 * Copy a code. Clipboard access needs a secure page; on plain http the code is selected instead so the person can
 * copy it by hand. `say` reports what happened.
 */
export async function copy(text, element, say) {
  try {
    await navigator.clipboard.writeText(text)
    say('Đã sao chép.')
  } catch {
    const range = document.createRange()
    range.selectNodeContents(element)
    const selection = window.getSelection()
    selection.removeAllRanges()
    selection.addRange(range)
    say('Đã chọn mã; nhấn giữ hoặc Ctrl+C để sao chép.')
  }
}

/** The server's answer as JSON, with its message as the error. */
export async function ask(path, init) {
  let response
  try {
    response = await fetch(path, init)
  } catch {
    throw new Error('Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.message || `Máy chủ báo lỗi ${response.status}.`)
    error.code = data.error
    error.status = response.status
    throw error
  }
  return data
}

/** Follow the device's light or dark setting: the kit's dark tokens key on data-theme. */
export function followScheme() {
  const query = window.matchMedia?.('(prefers-color-scheme: dark)')
  const apply = () => (document.documentElement.dataset.theme = query?.matches ? 'dark' : 'light')
  apply()
  query?.addEventListener?.('change', apply)
}
