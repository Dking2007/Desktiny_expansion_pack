<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Chính sách bảo mật

## Báo lỗ hổng

Vui lòng **không** mở issue công khai cho lỗ hổng bảo mật. Hãy dùng **Security › Report a vulnerability** (GitHub
private security advisory) của repo
[Dking2007/Desktiny_expansion_pack](https://github.com/Dking2007/Desktiny_expansion_pack/security/advisories/new).
Nêu phiên bản hoặc commit, các bước tái hiện và ảnh hưởng.

## Phạm vi

Trong phạm vi: máy chủ plugin dùng chung (`lib/`), các plugin và gói giao diện trong `expansion/`, công cụ đóng gói và
cấu hình triển khai trong `deploy/`.

Ngoài phạm vi: lỗi của chính Desktiny (báo ở [DXOS_Desktiny](https://github.com/Dking2007/DXOS_Desktiny)) và của các
thành phần bên thứ ba như Docker hay reverse proxy.

## Giới hạn đã biết

Xem mục "Giới hạn" trong [README](README.md): chấm công GPS tin vị trí do trình duyệt báo, cổng tiếp nhận lưu CCCD và
số điện thoại không mã hóa, chữ ký số là mô phỏng. Những điều này đã được ghi nhận, không cần báo lại như lỗ hổng mới.

## Không commit bí mật

`deploy/.env` bị `.gitignore` loại trừ. Nếu lỡ commit khóa hoặc mật khẩu, hãy xoay (rotate) ngay.
