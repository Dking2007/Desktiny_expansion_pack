<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Chính sách bảo mật

Các plugin ở đây chạm tới hồ sơ, tài khoản và tệp của Desktiny (có thể gồm số CCCD, số điện thoại), nên một lỗ hổng có
thể làm lộ hoặc sửa dữ liệu thật. Vì vậy **đừng mở issue công khai** cho lỗ hổng; hãy báo riêng theo mục dưới.

## Phiên bản được hỗ trợ

| Phiên bản | Nhận bản vá bảo mật |
|---|---|
| 1.1.x | Có (sau khi phát hành `v1.1.0`; hiện nhánh `main` là bản phát triển của 1.1.x) |
| Trước 1.1.0 | Không |

## Cách báo

Dùng **Security › Report a vulnerability** (báo cáo riêng của GitHub) tại
<https://github.com/Dking2007/Desktiny_expansion_pack/security/advisories/new>.

Nên gửi kèm:
- phiên bản hoặc commit của repo này và phiên bản Desktiny;
- bản mở rộng và plugin liên quan;
- các bước tái hiện, ảnh hưởng, và đề xuất sửa nếu có.

## Thời gian phản hồi (mục tiêu)

| Việc | Mục tiêu |
|---|---|
| Xác nhận đã nhận | trong 3 ngày |
| Đánh giá mức độ | trong 7 ngày |
| Có bản vá | trong 30 ngày, tùy mức độ và độ phức tạp |

Đây là cam kết cố gắng của nhóm nhỏ, không phải thỏa thuận mức dịch vụ.

## Phạm vi

Trong phạm vi: máy chủ plugin dùng chung (`lib/mo_rong`), các plugin và gói giao diện trong `expansion/`, SDK trang
(`sdk/`), công cụ đóng gói (`scripts/`) và cấu hình triển khai trong `deploy/`.

Ngoài phạm vi: lỗi của chính Desktiny (báo ở [DXOS_Desktiny](https://github.com/Dking2007/DXOS_Desktiny)), của các
thành phần bên thứ ba như Docker hay reverse proxy (báo cho dự án đó), và cấu hình thử trên máy cá nhân
(`base_url` là `localhost`).

## Công bố

Chúng tôi phối hợp với người báo: sửa trước, công bố sau, và ghi công người báo (nếu họ đồng ý) trong Security
Advisory và [CHANGELOG](CHANGELOG.md).

## Giới hạn đã biết

Xem mục "Giới hạn" trong [README](README.md): chấm công GPS tin vị trí do trình duyệt báo, cổng tiếp nhận lưu CCCD và
số điện thoại không mã hóa, chữ ký số là mô phỏng. Những điều này đã được ghi nhận, không cần báo lại như lỗ hổng mới.

## Không commit bí mật

`deploy/.env` bị `.gitignore` loại trừ. Token và khóa ký của plugin chỉ để trong tệp đó. Nếu lỡ commit khóa hoặc mật
khẩu, hãy xoay (rotate) ngay.
