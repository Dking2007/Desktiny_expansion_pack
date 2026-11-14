// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
// Read the text of a submitted paper (plain text, or a PDF that carries text) and find the usual details of a
// Vietnamese identity or tax paper in it. Everything runs in the page; nothing is sent anywhere.

const decoder = new TextDecoder('utf-8')

/** Text of a .txt file, or of a PDF's text operators (FlateDecode streams are inflated in the browser). */
export async function textOf(bytes, type = '', name = '') {
  const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes)
  const isPdf = /pdf/i.test(type) || /\.pdf$/i.test(name) || latin1(data.subarray(0, 5)) === '%PDF-'
  if (!isPdf) return decoder.decode(data)
  const raw = latin1(data)
  const parts = []
  const streams = /<<([\s\S]*?)>>\s*stream\r?\n/g
  let match
  while ((match = streams.exec(raw))) {
    const start = match.index + match[0].length
    const end = raw.indexOf('endstream', start)
    if (end < 0) break
    let stop = end
    while (stop > start && (data[stop - 1] === 0x0a || data[stop - 1] === 0x0d)) stop -= 1
    let body = data.subarray(start, stop)
    if (/\/FlateDecode/.test(match[1])) {
      try {
        body = await inflate(body)
      } catch {
        continue
      }
    }
    parts.push(textOperators(latin1(body)))
  }
  return parts.filter(Boolean).join('\n')
}

function latin1(bytes) {
  let text = ''
  for (let i = 0; i < bytes.length; i += 8192) text += String.fromCharCode(...bytes.subarray(i, i + 8192))
  return text
}

async function inflate(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'))
  return new Uint8Array(await new Response(stream).arrayBuffer())
}

/** Strings shown by Tj, TJ, ' and " operators, one line per text line. */
export function textOperators(content) {
  const lines = []
  let line = ''
  const tokens = /\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>|\[|\]|T\*|Tj|TJ|Td|TD|ET|'|"/g
  let pending = []
  for (const token of content.match(tokens) || []) {
    if (token.startsWith('(')) pending.push(unescape(token.slice(1, -1)))
    else if (token.startsWith('<') && token.length > 2) pending.push(hex(token.slice(1, -1)))
    else if (token === 'Tj' || token === 'TJ' || token === "'" || token === '"') {
      line += pending.join('')
      pending = []
      if (token === "'" || token === '"') {
        lines.push(line)
        line = ''
      }
    } else if (token === 'T*' || token === 'Td' || token === 'TD' || token === 'ET') {
      if (line) lines.push(line)
      line = ''
      pending = []
    }
  }
  if (line) lines.push(line)
  return lines.join('\n')
}

function unescape(text) {
  const raw = text.replace(/\\([nrtbf()\\]|[0-7]{1,3})/g, (_, c) => ({ n: '\n', r: '\r', t: '\t', b: '\b', f: '\f' })[c] ?? (/[0-7]/.test(c) ? String.fromCharCode(parseInt(c, 8)) : c))
  // Text written as UTF-8 bytes in a literal string (common for simple generators) reads back as UTF-8.
  try {
    return decoder.decode(Uint8Array.from(raw, (ch) => ch.charCodeAt(0) & 0xff))
  } catch {
    return raw
  }
}

function hex(text) {
  const clean = text.replace(/\s+/g, '')
  const bytes = []
  for (let i = 0; i < clean.length; i += 2) bytes.push(parseInt(clean.slice(i, i + 2).padEnd(2, '0'), 16))
  if (bytes[0] === 0xfe && bytes[1] === 0xff) {
    let out = ''
    for (let i = 2; i + 1 < bytes.length; i += 2) out += String.fromCharCode((bytes[i] << 8) | bytes[i + 1])
    return out
  }
  return String.fromCharCode(...bytes)
}

// "Họ và tên / Full name:" — an English label after a slash, then a colon, may follow the Vietnamese one.
const LABEL = String.raw`(?:\s*/\s*[A-Za-z][A-Za-z .,]*)?\s*[:：]?\s*`
function after(text, labels) {
  for (const label of labels) {
    const found = new RegExp(`(?:^|\\n)\\s*(?:${label})${LABEL}([^\\n]+)`, 'iu').exec(text)
    if (found) return found[1].trim().replace(/\s{2,}/g, ' ')
  }
  return ''
}
function isoDate(text) {
  const found = /(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})/.exec(text || '')
  if (!found) return ''
  const [day, month, year] = [Number(found[1]), Number(found[2]), Number(found[3])]
  if (month < 1 || month > 12 || day < 1 || day > 31) return ''
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}
function titleCase(name) {
  return name
    .toLocaleLowerCase('vi')
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toLocaleUpperCase('vi') + word.slice(1))
    .join(' ')
}

/**
 * Details found in the text, by the form field keys they fill. Only what is clearly there is returned;
 * a person checks every value before it is written into the dossier.
 */
export function recognize(text) {
  const t = String(text || '').normalize('NFC')
  const found = {}
  const idNumber = /(?:số|so|no\.?|số định danh|CCCD|CMND)[^\d\n]{0,25}(\d{12})\b/iu.exec(t) || /\b(0\d{11})\b/.exec(t)
  if (idNumber) found.so_cccd = idNumber[1]
  const name = after(t, ['Họ và tên', 'Họ, chữ đệm và tên', 'Họ tên', 'Full name', 'Ho va ten'])
  if (name) found.ho_ten = titleCase(name.replace(/[^\p{L}\s]/gu, '').trim())
  const born = after(t, ['Ngày, tháng, năm sinh', 'Ngày sinh', 'Date of birth', 'Ngay sinh'])
  if (isoDate(born)) found.ngay_sinh = isoDate(born)
  const sex = after(t, ['Giới tính', 'Sex', 'Gioi tinh'])
  if (/^n[ữu]/iu.test(sex) || /female/i.test(sex)) found.gioi_tinh = 'Nữ'
  else if (/^nam/iu.test(sex) || /\bmale/i.test(sex)) found.gioi_tinh = 'Nam'
  const origin = after(t, ['Quê quán', 'Place of origin', 'Que quan'])
  if (origin) found.que_quan = origin
  const home = after(t, ['Nơi thường trú', 'Nơi cư trú', 'Place of residence', 'Noi thuong tru', 'Địa chỉ'])
  if (home) found.noi_thuong_tru = home
  const tax = /(?:mã số thuế|MST|tax code)[^\d\n]{0,10}(\d{10}(?:-\d{3})?)\b/iu.exec(t)
  if (tax) found.ma_so_thue = tax[1]
  const phone = /(?:điện thoại|ĐT|SĐT|phone)[^\d\n+]{0,10}((?:\+84|0)[\d .]{9,13})/iu.exec(t)
  if (phone) found.so_dien_thoai = phone[1].replace(/[ .]/g, '')
  return found
}

export const FIELDS = {
  ho_ten: 'Họ và tên',
  ngay_sinh: 'Ngày sinh',
  gioi_tinh: 'Giới tính',
  so_cccd: 'Số định danh (CCCD)',
  que_quan: 'Quê quán',
  noi_thuong_tru: 'Nơi thường trú',
  ma_so_thue: 'Mã số thuế',
  so_dien_thoai: 'Số điện thoại',
}
