<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Nguồn gốc ảnh và GIF

Mọi ảnh chụp được chụp tự động bằng Playwright từ bản demo Desktiny đã cài các bản mở rộng, ngày 28/11/2026. Dữ liệu
trong ảnh là **dữ liệu mẫu giả**: tên người, cơ quan, số CCCD, số điện thoại và số hồ sơ đều không có thật. Hai sơ đồ
`*-dong.svg` vẽ tay, chuyển động bằng CSS và SMIL, không có script, phông hay ảnh ngoài; khi người xem bật giảm chuyển
động thì chỉ còn sơ đồ tĩnh.

| Tệp | Nội dung | Dùng ở | Nguồn |
|---|---|---|---|
| `vong-doi-ban-mo-rong-dong.svg` | Vòng đời bản mở rộng: đóng gói, cài và duyệt quyền, Desktiny chạy cùng máy chủ plugin và nguồn bên ngoài | [README](../../README.md), [README_EN](../../README_EN.md) mục Luồng dữ liệu | Vẽ tay SVG, 2026 |
| `luong-cam-bien-dong.svg` | Số đo vượt ngưỡng thành hồ sơ sự cố (hàng đợi, thử lại); hồ sơ kết thúc thành dòng JSONL nối sha256 | như trên, mục Các bản mẫu | Vẽ tay SVG, 2026 |
| `plugin-so-van-ban.png` | Plugin Sổ văn bản | như trên | Playwright, demo, 28/11/2026 |
| `plugin-cham-cong.png` | Plugin Chấm công | như trên | Playwright, demo, 28/11/2026 |
| `plugin-cam-bien.png` | Plugin Cảm biến thiết bị | như trên | Playwright, demo, 28/11/2026 |
| `plugin-luu-tru.png` | Plugin Lưu trữ lịch sử hồ sơ | như trên | Playwright, demo, 28/11/2026 |
| `cong-nop-dien-thoai.png` | Cổng nộp hồ sơ trực tuyến trên màn hình điện thoại | như trên | Playwright, demo, 28/11/2026 |
| `../media/gif-doi-nghiep-vu.gif` | Quản trị viên cài một gói, Desktiny đổi nghiệp vụ | như trên | Playwright (chuỗi khung hình), demo, 28/11/2026 |
| `../media/gif-cong-dan-nop.gif` | Người dân nộp hồ sơ, cán bộ nhận | như trên | Playwright (chuỗi khung hình), demo, 28/11/2026 |
| `goi-truoc-sau.png` | Trước và sau khi cài gói Một cửa | README, README_EN | Ghép bằng Pillow từ ảnh chụp Playwright, dữ liệu mẫu giả |
| `goi-mot-cua.png` | Trang chủ với gói Một cửa cấp xã | README, README_EN | Chụp bằng Playwright từ bản demo (mã nhánh tích hợp ngày 28/11/2026), dữ liệu mẫu giả |
| `goi-nhan-su.png` | Trang chủ với gói Nhân sự doanh nghiệp | README, README_EN | Chụp bằng Playwright từ bản demo (mã nhánh tích hợp ngày 28/11/2026), dữ liệu mẫu giả |
| `goi-van-thu.png` | Trang chủ với gói Văn thư – điều hành | README, README_EN | Chụp bằng Playwright từ bản demo (mã nhánh tích hợp ngày 28/11/2026), dữ liệu mẫu giả |
| `../media/gif-canh-bao-cam-bien.gif` | Cảm biến vượt ngưỡng tạo hồ sơ sự cố | README, README_EN | Chụp bằng Playwright từ bản demo (mã nhánh tích hợp ngày 28/11/2026), dữ liệu mẫu giả |

## Ảnh trong README của từng bản mở rộng

Chụp ở 1280×800 bằng Playwright từ một bản chạy thử Desktiny có dữ liệu mẫu giả (cùng quy ước như trên), lưu WebP. Ba bản có gói giao diện được chụp với gói của chính bản đó đang dùng.

| Thư mục | Tệp | Dùng ở | Nguồn |
|---|---|---|---|
| `expansion/mot-cua-xa/anh/` (11 ảnh) | `cap-so.webp`, `cong-nop-ho-so.webp`, `cong-tra-cuu.webp`, `cong-xac-thuc.webp`, `dang-nhap.webp`, `ky-so.webp`, `quy-trinh.webp`, `so-van-ban.webp`, `tiep-nhan.webp`, `tinh-han.webp`, `trang-chu.webp` | [README của bản Một cửa cấp xã](../../expansion/mot-cua-xa/README.md) | Playwright, bản chạy thử, 28/11/2026 |
| `expansion/nhan-su/anh/` (8 ảnh) | `bang-luong-kpi.webp`, `ca-lam-dia-diem.webp`, `cham-cong.webp`, `dang-nhap.webp`, `nhac-han.webp`, `phieu-luong.webp`, `quy-trinh.webp`, `trang-chu.webp` | [README của bản Nhân sự doanh nghiệp](../../expansion/nhan-su/README.md) | Playwright, bản chạy thử, 28/11/2026 |
| `expansion/van-thu/anh/` (7 ảnh) | `dang-nhap.webp`, `ho-so.webp`, `quan-ly-so-den.webp`, `quy-trinh.webp`, `so-van-ban-den.webp`, `trang-chu.webp`, `vao-so.webp` | [README của bản Văn thư – điều hành](../../expansion/van-thu/README.md) | Playwright, bản chạy thử, 28/11/2026 |
| `expansion/van-hanh/anh/` (2 ảnh) | `quy-trinh-su-co.webp`, `thiet-bi-cam-bien.webp` | [README của bản Vận hành – giám sát thiết bị](../../expansion/van-hanh/README.md) | Playwright, bản chạy thử, 28/11/2026 |
| `expansion/quan-tri-du-lieu/anh/` (1 ảnh) | `luu-tru-lich-su.webp` | [README của bản Quản trị dữ liệu](../../expansion/quan-tri-du-lieu/README.md) | Playwright, bản chạy thử, 28/11/2026 |

Logo của các bản mẫu nằm ở `expansion/<tên>/packs/<tên>/assets/logo.svg`, không thuộc thư mục này.
