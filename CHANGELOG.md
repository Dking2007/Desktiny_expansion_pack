<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Changelog

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/), đánh phiên bản theo
[SemVer](https://semver.org/lang/vi/).

## [Unreleased]

Bản phát hành đầu tiên của Desktiny Expansion Pack. Cần Desktiny 3.1.0 trở lên.

### Added
- Bộ khung máy chủ plugin dùng chung (`lib/`), SDK cho trang plugin và phông chữ đi kèm.
- Công cụ đóng gói (`scripts/dong_goi.py`, `build.bat`, `build.sh`), cấu hình triển khai (`deploy/`) và bộ kiểm thử
  cài thật vào Desktiny (`tests/desktiny`).
- Bản mở rộng Một cửa cấp xã: Tiếp nhận hồ sơ trực tuyến, Sổ văn bản, Ký số mô phỏng, Tính hạn ngày làm việc, Đọc giấy
  tờ.
- Bản mở rộng Nhân sự: Chấm công GPS, Tiền lương và KPI, Nhắc hạn hồ sơ.
- Bản mở rộng Văn thư – điều hành: gói giao diện và plugin Sổ văn bản đến; dùng chung plugin của bản khác qua
  `dung-chung.json`.
- Luồng tự động (cài ở trạng thái tắt) trong gói Nhân sự, Một cửa và Văn thư.
- Chọn gói giao diện và plugin cần đóng gói (`build.bat`, `dong_goi.py [TÊN ...]`, `make build CHON="..."`).
- Giao diện trực quan cho các plugin Chấm công, Tiền lương và KPI, Nhắc hạn, Sổ văn bản, Ký số, Tiếp nhận, Tính hạn,
  Đọc giấy tờ và Sổ văn bản đến.

### Changed
- Tách theo bản mở rộng: `expansion/<tên>/{packs,plugins}`; mỗi bản có README riêng.
- Máy chủ plugin trả mọi lỗi dạng JSON; lỗi ngoài dự kiến được ghi nhật ký, không lộ chi tiết.

### Fixed
- Máy chủ plugin từ chối `Content-Length` âm.
- Tra cứu hồ sơ trên cổng trực tuyến có giới hạn tần suất.
- Sự kiện của cổng tiếp nhận được xếp hàng và gửi lại khi Desktiny lỗi, không mất hồ sơ.
- Mặc định lương theo Nghị định 161/2026/NĐ-CP (lương cơ sở 2.530.000 đồng) và thuế thu nhập cá nhân 5 bậc theo
  Luật 109/2025/QH15.
- Phiếu ký số giữ dấu tiếng Việt (tệp Word .docx) và ghi rõ chữ ký là mô phỏng.

### Security
- Chỉ người được giao mới cấp số văn bản, ký và chốt KPI; người tạo không tự ký được hồ sơ của mình.
- Tệp CSV xuất ra chặn công thức: ô bắt đầu bằng `=`, `+`, `-`, `@` được thêm dấu `'` phía trước để bảng tính không chạy.
- Chỉ tin `X-Forwarded-For` khi bật `TRUST_PROXY=1` (máy chủ sau reverse proxy).
- Sổ văn bản chỉ hiện số của hồ sơ người xem mở được và số họ tự cấp.
