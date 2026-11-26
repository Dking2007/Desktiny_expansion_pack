// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { deflateSync } from 'node:zlib'
import { CHECK, SURE, analyze, idNumberParts, paperKind, recognize, taxCodeChecks, textOf } from '../../expansion/mot-cua-xa/plugins/doc-giay-to/ui/nhan-dang.js'

const CARD = `CĂN CƯỚC CÔNG DÂN
Số / No.: 001190012345
Họ và tên / Full name: NGUYỄN THỊ MAI
Ngày sinh / Date of birth: 05/03/1990
Giới tính / Sex: Nữ
Quê quán / Place of origin: Xã Đông La, Hoài Đức, Hà Nội
Nơi thường trú / Place of residence: Thôn 3, xã Mẫu, tỉnh Mẫu
Điện thoại: 0912 345 678
Mã số thuế: 0101234567`

test('the details of an identity paper are found', () => {
  assert.deepEqual(recognize(CARD), {
    so_cccd: '001190012345',
    ho_ten: 'Nguyễn Thị Mai',
    ngay_sinh: '1990-03-05',
    gioi_tinh: 'Nữ',
    que_quan: 'Xã Đông La, Hoài Đức, Hà Nội',
    noi_thuong_tru: 'Thôn 3, xã Mẫu, tỉnh Mẫu',
    ma_so_thue: '0101234567',
    so_dien_thoai: '0912345678',
  })
  assert.deepEqual(recognize('Không có gì ở đây'), {})
})

test('text is read from plain files and from compressed PDF streams', async () => {
  assert.equal(await textOf(new TextEncoder().encode('Họ tên: An'), 'text/plain'), 'Họ tên: An')
  const content = Buffer.from('BT /F1 12 Tf (Ho va ten: TRAN VAN BINH) Tj T* (So: 001090000001) Tj ET')
  const stream = deflateSync(content)
  const pdf = Buffer.concat([
    Buffer.from(`%PDF-1.4\n1 0 obj\n<< /Length ${stream.length} /Filter /FlateDecode >>\nstream\n`),
    stream,
    Buffer.from('\nendstream\nendobj\n%%EOF'),
  ])
  const text = await textOf(new Uint8Array(pdf), 'application/pdf', 'cccd.pdf')
  assert.match(text, /Ho va ten: TRAN VAN BINH\nSo: 001090000001/)
  assert.equal(recognize(text).so_cccd, '001090000001')
})

test('each value says how sure it is, and the id number is checked against the birth date and sex', () => {
  const found = analyze(CARD)
  // 001190012345: province 001, digit 1 = female born 1900–1999, year …90.
  assert.equal(found.so_cccd.confidence >= SURE, true)
  assert.match(found.so_cccd.note, /Khớp/)
  assert.equal(found.ho_ten.confidence >= SURE, true)
  const wrong = analyze(CARD.replace('Giới tính / Sex: Nữ', 'Giới tính / Sex: Nam'))
  assert.equal(wrong.so_cccd.confidence < SURE, true)
  assert.match(wrong.so_cccd.note, /giới tính/)
  assert.equal(analyze('Ngày sinh: 30/02/1990').ngay_sinh.confidence < CHECK, true)
  assert.equal(analyze('Địa chỉ: Thôn 3, xã Mẫu').noi_thuong_tru.confidence, CHECK)
  assert.deepEqual(idNumberParts('036205000123'), { province: 36, validProvince: true, sex: 'Nam', year: 2005 })
  assert.equal(paperKind(CARD), 'Căn cước')
})

test('tax codes are checked by their check digit', () => {
  // 0100109106: 31·0+29·1+23·0+19·0+17·1+13·0+7·9+5·1+3·0 = 114, 114 mod 11 = 4, 10 − 4 = 6.
  assert.equal(taxCodeChecks('0100109106'), true)
  assert.equal(taxCodeChecks('0100109107'), false)
  assert.equal(analyze('Mã số thuế: 0100109106').ma_so_thue.confidence > SURE, true)
})
