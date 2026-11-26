// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Page side shared by the expansion plugins: connect to Desktiny, call the plugin's own server as the
// person looking at the page (session token in X-Desktiny-Session), and small DOM helpers.
import { connect } from './desktiny-plugin-sdk.js'

export const desktiny = connect()

/** Call this plugin's own server (same origin as the page) as the viewer. */
export async function server(path, { method = 'GET', body } = {}) {
  const session = await desktiny.token()
  const response = await fetch(new URL(path, document.baseURI).href.replace('/ui/', '/'), {
    method,
    headers: { 'X-Desktiny-Session': session.token, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.message || `Lỗi ${response.status}`)
  return data
}

export const $ = (selector, root = document) => root.querySelector(selector)

/** Build an element: h('td', { class: 'num' }, 'text', child). Text is set as text, never as HTML. */
export function h(tag, attributes = {}, ...children) {
  const element = document.createElement(tag)
  for (const [key, value] of Object.entries(attributes || {})) {
    if (value === false || value === null || value === undefined) continue
    if (key.startsWith('on')) element.addEventListener(key.slice(2), value)
    else element.setAttribute(key, value === true ? '' : String(value))
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue
    element.append(child instanceof Node ? child : document.createTextNode(String(child)))
  }
  return element
}

export function money(value) {
  return `${Math.round(Number(value) || 0).toLocaleString('vi-VN')} đ`
}

export function show(element, message, tone = '') {
  element.textContent = message
  element.className = tone
}

/** This month as 'YYYY-MM' on the viewer's clock (toISOString would give the UTC month around midnight). */
export function thisMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}
