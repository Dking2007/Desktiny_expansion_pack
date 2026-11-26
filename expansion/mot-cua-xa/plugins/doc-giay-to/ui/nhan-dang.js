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
/** The value after the first label found, and which label it was (its index in `labels`). */
function labelled(text, labels) {
  for (const [index, label] of labels.entries()) {
    const found = new RegExp(`(?:^|\\n)\\s*(?:${label})${LABEL}([^\\n]+)`, 'iu').exec(text)
    if (found) return { value: found[1].trim().replace(/\s{2,}/g, ' '), index }
  }
  return { value: '', index: -1 }
}
const after = (text, labels) => labelled(text, labels).value
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
/** A date that exists on the calendar ("2026-02-30" does not). */
function realDate(value) {
  const [y, m, d] = value.split('-').map(Number)
  const date = new Date(Date.UTC(y, m - 1, d))
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d
}

/**
 * The 12-digit personal identification number: 3 digits of the province of birth registration (001–096), one digit
 * for sex and century (0/1: male/female born 1900–1999, 2/3: 2000–2099, …), then the last two digits of the year.
 */
export function idNumberParts(number) {
  if (!/^\d{12}$/.test(String(number || ''))) return null
  const province = Number(number.slice(0, 3))
  const code = Number(number[3])
  const century = 1900 + Math.floor(code / 2) * 100
  return { province, validProvince: province >= 1 && province <= 96, sex: code % 2 ? 'Nữ' : 'Nam', year: century + Number(number.slice(4, 6)) }
}

/** A 10-digit tax code's check digit (the 10th) matches the first nine. */
export function taxCodeChecks(code) {
  const digits = String(code || '').slice(0, 10)
  if (!/^\d{10}$/.test(digits)) return false
  const weights = [31, 29, 23, 19, 17, 13, 7, 5, 3]
  const sum = weights.reduce((total, weight, i) => total + weight * Number(digits[i]), 0)
  return (10 - (sum % 11)) % 10 === Number(digits[9])
}

/** What kind of paper the text is, from its title. */
export function paperKind(text) {
  const t = String(text || '').normalize('NFC')
  if (/căn cước|can cuoc|identity card/iu.test(t)) return 'Căn cước'
  if (/chứng minh nhân dân|chung minh nhan dan/iu.test(t)) return 'Chứng minh nhân dân'
  if (/hộ chiếu|passport/iu.test(t)) return 'Hộ chiếu'
  if (/đăng ký thuế|thông báo mã số thuế|tax registration/iu.test(t)) return 'Giấy tờ thuế'
  return 'Giấy tờ'
}

/** How sure a value is: high when the label and the format both agree, lower when something only looks right. */
export const SURE = 0.9
export const CHECK = 0.6

/**
 * Details found in the text with how sure each one is: { key: { value, confidence (0–1), note } }. A note says
 * why a value needs a closer look (or what was checked). A person checks every value before it is written.
 */
export function analyze(text) {
  const t = String(text || '').normalize('NFC')
  const found = {}
  const put = (key, value, confidence, note = '') => (found[key] = { value, confidence, note })

  const name = after(t, ['Họ và tên', 'Họ, chữ đệm và tên', 'Họ tên', 'Full name', 'Ho va ten'])
  if (name) {
    const clean = titleCase(name.replace(/[^\p{L}\s]/gu, '').trim())
    const words = clean.split(' ').length
    if (clean !== titleCase(name)) put('ho_ten', clean, CHECK, 'Đã bỏ ký tự lạ trong tên.')
    else if (words < 2 || words > 6) put('ho_ten', clean, CHECK, 'Tên có số chữ bất thường.')
    else put('ho_ten', clean, 0.95)
  }

  const born = isoDate(after(t, ['Ngày, tháng, năm sinh', 'Ngày sinh', 'Date of birth', 'Ngay sinh']))
  if (born) {
    const year = Number(born.slice(0, 4))
    if (!realDate(born)) put('ngay_sinh', born, 0.3, 'Ngày này không có trên lịch.')
    else if (year < 1900 || year > new Date().getFullYear()) put('ngay_sinh', born, 0.4, 'Năm sinh bất thường.')
    else put('ngay_sinh', born, 0.95)
  }

  const sex = after(t, ['Giới tính', 'Sex', 'Gioi tinh'])
  if (/^n[ữu]/iu.test(sex) || /female/i.test(sex)) put('gioi_tinh', 'Nữ', 0.95)
  else if (/^nam/iu.test(sex) || /\bmale/i.test(sex)) put('gioi_tinh', 'Nam', 0.95)

  const labelledId = /(?:số|so|no\.?|số định danh|CCCD|CMND)[^\d\n]{0,25}(\d{12})\b/iu.exec(t)
  const idNumber = labelledId || /\b(0\d{11})\b/.exec(t)
  if (idNumber) {
    const parts = idNumberParts(idNumber[1])
    const notes = []
    if (!labelledId) notes.push('Không thấy nhãn “Số” cạnh dãy số.')
    if (!parts.validProvince) notes.push('Ba chữ số đầu không phải mã tỉnh.')
    if (found.ngay_sinh && parts.year !== Number(found.ngay_sinh.value.slice(0, 4))) notes.push('Không khớp năm sinh.')
    if (found.gioi_tinh && parts.sex !== found.gioi_tinh.value) notes.push('Không khớp giới tính.')
    const crossChecked = Boolean(found.ngay_sinh && found.gioi_tinh)
    if (notes.length) put('so_cccd', idNumber[1], notes.length > 1 ? 0.35 : CHECK, notes.join(' '))
    else put('so_cccd', idNumber[1], crossChecked ? 0.98 : SURE, crossChecked ? 'Khớp năm sinh và giới tính.' : '')
  }

  const origin = after(t, ['Quê quán', 'Place of origin', 'Que quan'])
  if (origin) put('que_quan', origin, origin.length >= 6 ? SURE : CHECK, origin.length >= 6 ? '' : 'Địa chỉ quá ngắn.')
  const home = labelled(t, ['Nơi thường trú', 'Nơi cư trú', 'Place of residence', 'Noi thuong tru', 'Địa chỉ'])
  if (home.value) {
    if (home.index === 4) put('noi_thuong_tru', home.value, CHECK, 'Lấy từ dòng “Địa chỉ”, có thể không phải nơi thường trú.')
    else put('noi_thuong_tru', home.value, home.value.length >= 6 ? SURE : CHECK, home.value.length >= 6 ? '' : 'Địa chỉ quá ngắn.')
  }

  const tax = /(?:mã số thuế|MST|tax code)[^\d\n]{0,10}(\d{10}(?:-\d{3})?)\b/iu.exec(t)
  if (tax) {
    const checks = taxCodeChecks(tax[1])
    put('ma_so_thue', tax[1], checks ? 0.95 : CHECK, checks ? 'Chữ số kiểm tra hợp lệ.' : 'Chữ số kiểm tra không khớp, nên đối chiếu.')
  }

  const phone = /(?:điện thoại|ĐT|SĐT|phone)[^\d\n+]{0,10}((?:\+84|0)[\d .]{9,13})/iu.exec(t)
  if (phone) {
    const number = phone[1].replace(/[ .]/g, '')
    const valid = /^(?:0|\+84)[35789]\d{8}$/.test(number) || /^02\d{9}$/.test(number)
    put('so_dien_thoai', number, valid ? SURE : CHECK, valid ? '' : 'Độ dài hoặc đầu số lạ.')
  }
  return found
}

/**
 * Details found in the text, by the form field keys they fill. Only what is clearly there is returned;
 * a person checks every value before it is written into the dossier.
 */
export function recognize(text) {
  return Object.fromEntries(Object.entries(analyze(text)).map(([key, item]) => [key, item.value]))
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
