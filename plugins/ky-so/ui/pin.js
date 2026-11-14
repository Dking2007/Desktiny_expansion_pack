// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// The signer's PIN: set once on this page, then asked for every signature.
import { $, h, server, show } from './mo-rong.js'

export async function pinBox(holder) {
  const me = await server('/api/toi')
  if (me.has_pin) return me
  const pin = h('input', { type: 'password', inputmode: 'numeric', minlength: 6, maxlength: 12, placeholder: '6–12 chữ số' })
  const again = h('input', { type: 'password', inputmode: 'numeric', minlength: 6, maxlength: 12 })
  const status = h('p')
  holder.replaceChildren(
    h('div', { class: 'card' }, h('strong', {}, 'Đặt mã PIN ký'), h('p', { class: 'muted' }, 'Mã PIN dùng để xác nhận mỗi lần ký; không ai khác biết.'),
      h('div', { class: 'grid' }, h('label', {}, 'PIN', pin), h('label', {}, 'Nhập lại', again)),
      h('button', { type: 'button', onclick: async () => {
        if (pin.value !== again.value) return show(status, 'Hai lần nhập không khớp.', 'bad')
        try {
          await server('/api/pin', { method: 'POST', body: { pin: pin.value } })
          location.reload()
        } catch (error) {
          show(status, error.message, 'bad')
        }
      } }, 'Lưu PIN'), status),
  )
  return null
}
