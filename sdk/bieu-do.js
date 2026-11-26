// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Small charts and building blocks for plugin pages, drawn with plain DOM and SVG (no library, nothing loaded from
// outside). Styles are in giao-dien.css. Text is always set as text, never as HTML.
import { h } from './mo-rong.js'

const SVG = 'http://www.w3.org/2000/svg'

/** Build an SVG element: s('circle', { r: 4 }). */
export function s(tag, attributes = {}, ...children) {
  const element = document.createElementNS(SVG, tag)
  for (const [key, value] of Object.entries(attributes || {})) {
    if (value !== null && value !== undefined && value !== false) element.setAttribute(key, String(value))
  }
  for (const child of children.flat()) if (child) element.append(child)
  return element
}

// Simple line icons, 24×24, drawn for this kit.
const ICONS = {
  clock: ['M12 7v5l3 2', 'circle:12,12,9'],
  pin: ['M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z', 'circle:12,10,2.5'],
  calendar: ['M4 6h16v14H4z', 'M4 10h16', 'M8 3v4', 'M16 3v4'],
  alert: ['M12 3 2 20h20L12 3z', 'M12 10v4', 'M12 17.5v.5'],
  check: ['M5 12.5 10 17 19 7'],
  wallet: ['M3 7h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z', 'M3 7l12-4 2 4', 'circle:16.5,13.5,1.2'],
  trend: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'],
  users: ['circle:9,8,3.5', 'M2.5 20a6.5 6.5 0 0 1 13 0', 'M16 4.5a3.5 3.5 0 0 1 0 7', 'M18 14a6 6 0 0 1 3.5 6'],
  bell: ['M6 16V11a6 6 0 0 1 12 0v5l2 2H4l2-2z', 'M10 20a2 2 0 0 0 4 0'],
  file: ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 12h6', 'M9 16h6'],
  star: ['M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.5 9.7l5.9-.9L12 3.5z'],
  login: ['M10 17l5-5-5-5', 'M15 12H3', 'M14 4h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-5'],
  logout: ['M15 17l5-5-5-5', 'M20 12H8', 'M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h5'],
  settings: ['circle:12,12,3', 'M12 2v3', 'M12 19v3', 'M2 12h3', 'M19 12h3', 'M4.9 4.9l2.1 2.1', 'M17 17l2.1 2.1', 'M4.9 19.1 7 17', 'M17 7l2.1-2.1'],
  plus: ['M12 5v14', 'M5 12h14'],
  chevronLeft: ['M15 6l-6 6 6 6'],
  chevronRight: ['M9 6l6 6-6 6'],
  download: ['M12 4v11', 'M7 10l5 5 5-5', 'M5 20h14'],
  lock: ['M6 11h12v9H6z', 'M8.5 11V8a3.5 3.5 0 0 1 7 0v3'],
  refresh: ['M20 11a8 8 0 1 0-2.3 5.7', 'M20 5v6h-6'],
}

/** An inline icon: icon('clock', 16). Decorative: hidden from screen readers. */
export function icon(name, size = 16) {
  const parts = ICONS[name] || []
  return s(
    'svg',
    { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.9, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', class: 'gd-svg-icon' },
    parts.map((part) => {
      if (!part.startsWith('circle:')) return s('path', { d: part })
      const [cx, cy, r] = part.slice(7).split(',')
      return s('circle', { cx, cy, r })
    }),
  )
}

/** A stable colour per person, from their name. */
export function hue(name) {
  let total = 0
  for (const char of String(name || '')) total = (total * 31 + char.charCodeAt(0)) % 360
  return total
}

/** "Nguyễn Thị Lan" → "NL". */
export function initials(name) {
  const words = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (!words.length) return '?'
  return ((words[0][0] || '') + (words.length > 1 ? words[words.length - 1][0] : '')).toLocaleUpperCase('vi')
}

export function avatar(name, large = false) {
  return h('span', { class: `gd-avatar${large ? ' lg' : ''}`, style: `--hue:${hue(name)}`, 'aria-hidden': 'true' }, initials(name))
}

export function chip(text, tone = 'muted', iconName) {
  return h('span', { class: `gd-chip tone-${tone}` }, iconName ? icon(iconName, 13) : null, text)
}

/** A stat tile: stat({ label, value, hint, tone, icon }). */
export function stat({ label, value, hint, tone = 'accent', icon: iconName }) {
  return h(
    'div',
    { class: `gd-stat tone-${tone}` },
    h('span', { class: 'gd-stat-label' }, iconName ? h('span', { class: 'gd-icon' }, icon(iconName, 15)) : null, label),
    h('span', { class: 'gd-stat-value' }, value ?? '—'),
    hint ? h('span', { class: 'gd-stat-hint' }, hint) : null,
  )
}

export function empty(title, text, iconName = 'file') {
  return h('div', { class: 'gd-empty' }, icon(iconName, 28), h('strong', {}, title), text ? h('span', {}, text) : null)
}

/** A ring gauge: ring({ value: 72, max: 100, label: '72', sub: 'điểm', tone: 'ok', size: 120 }). */
export function ring({ value = 0, max = 100, label, sub, tone = 'accent', size = 120, stroke = 11 }) {
  const radius = (size - stroke) / 2
  const length = 2 * Math.PI * radius
  const share = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0
  const progress = s('circle', { class: 'gd-ring-value', cx: size / 2, cy: size / 2, r: radius, fill: 'none', 'stroke-width': stroke, 'stroke-dasharray': length, 'stroke-dashoffset': length })
  requestAnimationFrame(() => progress.setAttribute('stroke-dashoffset', String(length * (1 - share))))
  return h(
    'div',
    { class: `gd-ring tone-${tone}`, role: 'img', 'aria-label': `${label ?? value}${sub ? ' ' + sub : ''}` },
    s('svg', { width: size, height: size, viewBox: `0 0 ${size} ${size}` }, s('circle', { class: 'gd-ring-track', cx: size / 2, cy: size / 2, r: radius, fill: 'none', 'stroke-width': stroke }), progress),
    h('span', { class: 'gd-ring-text', 'aria-hidden': 'true' }, h('strong', {}, label ?? value), sub ? h('small', {}, sub) : null),
  )
}

/** Labelled horizontal bars: bars([{ label, value, tone, text }], { max }). */
export function bars(items, { max, format = (v) => v } = {}) {
  const top = max ?? Math.max(1, ...items.map((item) => Number(item.value) || 0))
  return h(
    'div',
    { class: 'gd-bars' },
    items.map((item) =>
      h(
        'div',
        { class: `gd-bar-row tone-${item.tone || 'accent'}` },
        h('span', { class: 'gd-title', title: item.label }, item.label),
        h('span', { class: 'gd-bar-track' }, h('span', { class: 'gd-bar-fill', style: `width:${Math.max(0, Math.min(100, ((Number(item.value) || 0) / top) * 100))}%` })),
        h('span', { class: 'num' }, item.text ?? format(item.value)),
      ),
    ),
  )
}

/** One bar split into parts, with a legend: stack([{ label, value, tone }], { format }). */
export function stack(parts, { format = (v) => v } = {}) {
  const total = parts.reduce((sum, part) => sum + Math.max(0, Number(part.value) || 0), 0) || 1
  const shown = parts.filter((part) => Number(part.value) > 0)
  return h(
    'div',
    {},
    h('div', { class: 'gd-stack', role: 'img', 'aria-label': shown.map((p) => `${p.label} ${format(p.value)}`).join(', ') },
      shown.map((part) => h('span', { class: `tone-${part.tone || 'accent'}`, style: `width:${(Number(part.value) / total) * 100}%`, title: `${part.label}: ${format(part.value)}` }))),
    h('div', { class: 'gd-legend' }, shown.map((part) => h('span', { class: `tone-${part.tone || 'accent'}` }, h('i', { class: 'gd-dot' }), `${part.label}: ${format(part.value)}`))),
  )
}

/** A small line chart of numbers in order: spark([3, 5, 4], { width, height, tone }). */
export function spark(values, { width = 160, height = 44, tone = 'accent', label = '' } = {}) {
  const numbers = values.map((v) => Number(v) || 0)
  if (numbers.length < 2) numbers.unshift(numbers[0] ?? 0)
  const highest = Math.max(...numbers)
  const lowest = Math.min(...numbers)
  const pad = (highest - lowest || Math.abs(highest) || 1) * 0.25
  const top = highest + pad
  const bottom = lowest - pad
  const span = top - bottom || 1
  const step = width / (numbers.length - 1)
  const points = numbers.map((v, i) => [i * step, height - 4 - ((v - bottom) / span) * (height - 8)])
  const line = points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lastX, lastY] = points[points.length - 1]
  return s(
    'svg',
    { class: `gd-spark tone-${tone}`, width, height, viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': label || numbers.join(', ') },
    s('path', { d: `M0,${height} L${line.replaceAll(' ', ' L')} L${width},${height} Z` }),
    s('polyline', { points: line }),
    s('circle', { cx: lastX, cy: lastY, r: 3 }),
  )
}

const WEEKDAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

/**
 * A month calendar, Monday first. `days` maps 'YYYY-MM-DD' to { tone, label, title }. Weekend days without data
 * are shown as days off; `onPick(day)` runs when a day is chosen.
 */
export function calendar(month, days = {}, { onPick, selected, today = localDay() } = {}) {
  const [year, number] = month.split('-').map(Number)
  const first = new Date(year, number - 1, 1)
  const count = new Date(year, number, 0).getDate()
  const offset = (first.getDay() + 6) % 7
  const cells = WEEKDAYS.map((name) => h('span', { class: 'gd-cal-head', 'aria-hidden': 'true' }, name))
  for (let i = 0; i < offset; i++) cells.push(h('span', { class: 'gd-cal-blank' }))
  for (let d = 1; d <= count; d++) {
    const key = `${month}-${String(d).padStart(2, '0')}`
    const info = days[key]
    const weekday = (offset + d - 1) % 7
    const classes = ['gd-cal-day']
    if (info?.tone) classes.push(`tone-${info.tone}`)
    else if (weekday >= 5) classes.push('off')
    if (key > today) classes.push('future')
    if (key === today) classes.push('today')
    cells.push(
      h(
        'button',
        {
          type: 'button',
          class: classes.join(' '),
          'aria-pressed': selected === key ? 'true' : 'false',
          'aria-label': `Ngày ${d}/${number}${info?.title ? ': ' + info.title : ''}`,
          title: info?.title || '',
          onclick: () => onPick?.(key),
        },
        h('span', { class: 'gd-cal-top' }, h('b', {}, d), info?.mark ? h('i', { class: `gd-mark tone-${info.tone || 'muted'}`, 'aria-hidden': 'true' }, info.mark) : null),
        info?.label ? h('small', {}, info.label) : null,
      ),
    )
  }
  return h('div', { class: 'gd-cal', role: 'group', 'aria-label': `Tháng ${number}/${year}` }, cells)
}

function minutesOf(value) {
  const [hours, mins] = String(value || '0:0').split(':').map(Number)
  return (hours || 0) * 60 + (mins || 0)
}

/**
 * A working day on one line: the shift, the time worked, the punches and "now".
 * day({ start: '08:00', end: '17:00', marks: [{ at: '08:05', label: 'Vào 08:05', tone: 'ok' }], worked: ['08:05', '12:00'] })
 */
export function day({ start = '08:00', end = '17:00', marks = [], worked, now } = {}) {
  const from = Math.max(0, minutesOf(start) - 90)
  const to = Math.min(24 * 60, minutesOf(end) + 90)
  const at = (value) => `${(((minutesOf(value) - from) / (to - from)) * 100).toFixed(2)}%`
  const width = (a, b) => `${(((minutesOf(b) - minutesOf(a)) / (to - from)) * 100).toFixed(2)}%`
  const axis = []
  for (let m = Math.ceil(from / 120) * 120; m <= to; m += 120) axis.push(`${String(m / 60).padStart(2, '0')}h`)
  const clock = now ?? new Date().toTimeString().slice(0, 5)
  const nowShown = minutesOf(clock) >= from && minutesOf(clock) <= to
  return h(
    'div',
    { class: 'gd-day', role: 'img', 'aria-label': `Ca ${start}–${end}. ${marks.map((m) => m.label).join('. ')}` },
    h('span', { class: 'gd-day-track' }),
    h('span', { class: 'gd-day-shift', style: `left:${at(start)};width:${width(start, end)}` }),
    worked ? h('span', { class: 'gd-day-worked', style: `left:${at(worked[0])};width:${width(worked[0], worked[1])}` }) : null,
    nowShown ? h('span', { class: 'gd-day-now', style: `left:${at(clock)}`, title: `Bây giờ ${clock}` }) : null,
    marks.map((mark) => h('span', { class: `gd-day-mark tone-${mark.tone || 'accent'}`, style: `left:${at(mark.at)}` }, mark.label)),
    h('span', { class: 'gd-day-axis', 'aria-hidden': 'true' }, axis.map((label) => h('span', {}, label))),
  )
}

/** Today as 'YYYY-MM-DD' on the viewer's clock (toISOString would give the UTC day). */
export function localDay(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

/** Days from today to a 'YYYY-MM-DD' date (negative: already past). */
export function daysUntil(value, from = new Date()) {
  const [y, m, d] = String(value).slice(0, 10).split('-').map(Number)
  const target = new Date(y, m - 1, d)
  const start = new Date(from.getFullYear(), from.getMonth(), from.getDate())
  return Math.round((target - start) / 86400000)
}

/** 'YYYY-MM' moved by n months. */
export function shiftMonth(month, n) {
  const [y, m] = month.split('-').map(Number)
  const date = new Date(y, m - 1 + n, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

export function monthName(month) {
  const [y, m] = month.split('-').map(Number)
  return `Tháng ${m}/${y}`
}

/** A month switcher (‹ Tháng 11/2026 ›); calls onChange with the new 'YYYY-MM'. */
export function monthStepper(month, onChange, { max } = {}) {
  const next = shiftMonth(month, 1)
  return h(
    'div',
    { class: 'gd-stepper' },
    h('button', { type: 'button', 'aria-label': 'Tháng trước', onclick: () => onChange(shiftMonth(month, -1)) }, icon('chevronLeft', 15)),
    h('strong', { 'aria-live': 'polite' }, monthName(month)),
    h('button', { type: 'button', 'aria-label': 'Tháng sau', disabled: max && next > max ? true : null, onclick: () => onChange(next) }, icon('chevronRight', 15)),
  )
}

/** Skeleton lines while loading. */
export function skeleton(lines = 3, height = 14) {
  return h('div', { 'aria-hidden': 'true', style: 'display:grid;gap:8px' }, Array.from({ length: lines }, (_, i) => h('div', { class: 'gd-skeleton', style: `height:${height}px;width:${90 - i * 12}%` })))
}

const WEEKDAY_NAMES = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy']

function dateOf(value) {
  if (value instanceof Date) return value
  const [y, m, d] = String(value).slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** Tờ lịch bloc: today's (or any) date as a tear-off calendar sheet, with an optional note at the foot. */
export function tear(value = new Date(), note) {
  const date = dateOf(value)
  return h(
    'div',
    { class: 'gd-tear', role: 'img', 'aria-label': `${WEEKDAY_NAMES[date.getDay()]}, ngày ${date.getDate()} tháng ${date.getMonth() + 1} năm ${date.getFullYear()}` },
    h('span', { class: 'gd-tear-month', 'aria-hidden': 'true' }, `Tháng ${date.getMonth() + 1}/${date.getFullYear()}`),
    h('span', { class: 'gd-tear-day', 'aria-hidden': 'true' }, date.getDate()),
    h('span', { class: 'gd-tear-weekday', 'aria-hidden': 'true' }, WEEKDAY_NAMES[date.getDay()]),
    note ? h('span', { class: 'gd-tear-note' }, note) : null,
  )
}

/** A small calendar leaf for a due date ('YYYY-MM-DD'): month on top, day below; tone 'bad' once passed. */
export function leaf(value, tone = 'muted') {
  const date = dateOf(value)
  return h(
    'span',
    { class: `gd-leaf tone-${tone}`, 'aria-hidden': 'true' },
    h('b', {}, `Th${date.getMonth() + 1}`),
    h('span', {}, date.getDate()),
  )
}

/** A mark from the paper attendance sheet: mark('✓', 'ok'), mark('M', 'warn'). */
export function mark(symbol, tone = 'muted', label = '') {
  return h('span', { class: `gd-mark tone-${tone}`, title: label || null, 'aria-label': label || null }, symbol)
}

/**
 * The heading of an administrative document (Nghị định 30 layout): docHead({ parent, agency, number, place, date }).
 * `date` is a Date or 'YYYY-MM-DD'; the place-and-date line reads "Xã A, ngày 26 tháng 11 năm 2026".
 */
export function docHead({ parent = '', agency = '', number = '', place = '', date } = {}) {
  const when = date ? dateOf(date) : null
  return h(
    'div',
    { class: 'gd-doc-head' },
    h('div', { class: 'gd-doc-agency' }, parent ? h('span', {}, parent.toLocaleUpperCase('vi')) : null, h('strong', {}, agency.toLocaleUpperCase('vi')), number ? h('div', { class: 'gd-doc-no' }, `Số: ${number}`) : null),
    h(
      'div',
      { class: 'gd-doc-nation' },
      h('strong', {}, 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM'),
      h('span', {}, 'Độc lập - Tự do - Hạnh phúc'),
      when ? h('div', { class: 'gd-doc-date' }, `${place ? place + ', ' : ''}ngày ${when.getDate()} tháng ${when.getMonth() + 1} năm ${when.getFullYear()}`) : null,
    ),
  )
}

/** A red ink stamp showing a state: seal('Đã ký số', '26/11/2026'). Not an emblem, not a real seal. */
export function seal(text, sub = '', tone = '') {
  return h('span', { class: `gd-seal${tone ? ' tone-' + tone : ''}`, role: 'img', 'aria-label': sub ? `${text}, ${sub}` : text }, h('span', { 'aria-hidden': 'true' }, text, sub ? h('small', {}, sub) : null))
}
