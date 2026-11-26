// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// The signer's PIN: set once (or changed) on these pages, then asked for every signature. Also the small pieces the
// two signing pages share: the document sheet, its file list, the stamp and how dates read.
import { h, server } from './mo-rong.js'
import { icon, seal } from './bieu-do.js'

/** '2026-11-26T09:15:00+07:00' → '26/11/2026'. */
export const dayOf = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
/** '2026-11-26T09:15:00+07:00' → '09:15'. */
export const timeOf = (iso) => iso.slice(11, 16)
/** A verification code in groups of four, easier to read aloud and to type. */
export const grouped = (code) => String(code).match(/.{1,4}/g)?.join(' ') ?? ''

/** A PIN field: { wrap, input }. */
export function pinField(label, { autocomplete = 'off', id } = {}) {
  const input = h('input', { id, type: 'password', inputmode: 'numeric', pattern: '[0-9]*', minlength: 6, maxlength: 12, autocomplete, placeholder: '6–12 chữ số', required: true })
  input.addEventListener('input', () => {
    const digits = input.value.replace(/\D/g, '')
    if (digits !== input.value) input.value = digits
  })
  const wrap = h('label', { class: 'ks-pin' }, label, h('span', { class: 'ks-pin-box' }, icon('lock', 17), input))
  return { wrap, input }
}

/** Where the viewer stands: { user, has_pin, locked }. */
export const whoAmI = () => server('/api/toi')

/**
 * Set (or, with `change`, change) the PIN in `holder`; `onDone` runs once it is saved. `onCancel` adds a "Thôi"
 * button (changing is optional, setting the first PIN is not).
 */
export function pinSetup(holder, { change = false, onDone, onCancel } = {}) {
  const old = change ? pinField('Mã PIN đang dùng') : null
  const pin = pinField(change ? 'Mã PIN mới' : 'Mã PIN', { autocomplete: 'new-password' })
  const again = pinField('Nhập lại', { autocomplete: 'new-password' })
  const status = h('p', { role: 'status', style: 'margin:0' })
  const form = h('form', { class: 'gd-panel', style: 'margin-bottom:16px', 'aria-labelledby': 'pin-title' },
    h('div', { class: 'gd-panel-head' }, h('h2', { id: 'pin-title' }, icon('lock', 17), change ? 'Đổi mã PIN ký' : 'Đặt mã PIN ký')),
    h('div', { class: 'gd-panel-body', style: 'display:grid;gap:14px' },
      h('p', { class: 'gd-sub', style: 'margin:0' }, change
        ? 'Nhập PIN đang dùng rồi chọn PIN mới.'
        : 'Mỗi lần ký, bạn xác nhận bằng mã PIN này. Chỉ bạn biết mã; máy chủ chỉ lưu dạng băm. Nhập sai 5 lần thì PIN bị khoá.'),
      h('div', { style: 'display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,200px),1fr));gap:12px' }, old?.wrap, pin.wrap, again.wrap),
      h('div', { class: 'ks-actions' },
        h('button', { type: 'submit' }, change ? 'Đổi PIN' : 'Lưu PIN'),
        onCancel ? h('button', { type: 'button', class: 'gd-ghost', onclick: onCancel }, 'Thôi') : null),
      status))
  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (pin.input.value !== again.input.value) {
      status.replaceChildren(h('span', { class: 'gd-note tone-bad' }, icon('alert', 15), 'Hai lần nhập PIN không khớp.'))
      return again.input.focus()
    }
    try {
      await server('/api/pin', { method: 'POST', body: { pin: pin.input.value, ...(old ? { pin_cu: old.input.value } : {}) } })
      holder.replaceChildren()
      onDone?.()
    } catch (error) {
      status.replaceChildren(h('span', { class: 'gd-note tone-bad', role: 'alert' }, icon('alert', 15), error.message))
    }
  })
  holder.replaceChildren(form)
  ;(old || pin).input.focus()
}

/** The viewer, when their PIN is set; otherwise the PIN form in `holder`, and `onReady` once it is saved. */
export async function pinBox(holder, onReady) {
  const me = await whoAmI()
  if (me.has_pin) return me
  pinSetup(holder, { onDone: () => whoAmI().then(onReady) })
  return null
}

/** The document sheet of a dossier: code, title, the flow's note, then `files` (a node) and a place for the stamp. */
export function sheet({ code, title, when, note, files }) {
  return h('article', { class: 'gd-doc ks-sheet', 'aria-label': `Hồ sơ ${code || ''} ${title}` },
    h('div', { class: 'ks-sheet-top' }, h('span', {}, code ? h('b', {}, code) : 'Hồ sơ'), when ? h('span', {}, when) : null),
    h('h2', {}, title),
    note ? h('blockquote', {}, note) : null,
    files,
    h('div', { class: 'ks-stamp-spot' }))
}

/** Land a stamp on a sheet made by sheet(). */
export function stamp(target, text, sub, tone = '') {
  const mark = seal(text, sub, tone)
  mark.classList.add('ks-landing')
  target.querySelector('.ks-stamp-spot').replaceChildren(mark)
  return mark
}

/** Checkbox rows for the files to sign; files signed before show who signed and the code. */
export function fileList(files, signatures = []) {
  const byFile = new Map(signatures.map((s) => [s.file_id, s]))
  // Files signed before are left unticked (signing again gives new codes), unless every file was.
  const allSigned = files.every((file) => byFile.has(file.id))
  return h('ul', { class: 'ks-files', 'aria-label': 'Tài liệu sẽ ký' },
    files.map((file) => {
      const done = byFile.get(file.id)
      return h('li', {}, h('label', {},
        h('input', { type: 'checkbox', value: file.id, checked: !done || allSigned ? true : null }),
        icon('file', 17),
        h('span', { class: 'ks-file-name' }, file.name,
          done ? h('small', {}, `Đã ký ngày ${dayOf(done.signed_at)} lúc ${timeOf(done.signed_at)}, ${done.signer_name}, mã ${grouped(done.code)}`) : null)))
    }))
}

/** The ids of the ticked files in a list made by fileList(). */
export const ticked = (list) => [...list.querySelectorAll('input:checked')].map((input) => input.value)
