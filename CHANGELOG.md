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
- Bản mở rộng Vận hành – giám sát thiết bị: plugin Cảm biến thiết bị (cổng 9208) nhận số đo qua HTTP có khóa thiết bị, vượt ngưỡng thì gửi sự kiện (giữ hàng chờ khi Desktiny lỗi) để mẫu luồng tạo hồ sơ sự cố; `scripts/gia_lap_cam_bien.py` giả lập số đo.
- Bản minh họa Quản trị dữ liệu: plugin Lưu trữ lịch sử hồ sơ (cổng 9209) chép hồ sơ đã duyệt, kết thúc (đã che CCCD, số điện thoại, email) ra tệp JSONL theo tháng có chuỗi băm sha256; kiểm toàn vẹn, truy nguồn về hồ sơ gốc, đánh dấu tháng cần chuyển kho lạnh.
- `scripts/kiem_phien_ban.py`: workflow phát hành kiểm số phiên bản theo SemVer; gói, plugin đổi nội dung phải tăng `version`.
- CI cài thử mọi gói và plugin vào Desktiny v3.1.0.
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
- Bộ giới hạn tần suất `Window` chuyển vào `lib/mo_rong` để các plugin dùng chung.
- Trang đăng nhập Một cửa đổi tiêu đề thành “Cổng làm việc của cán bộ” (không lặp tên ứng dụng).
- Tách theo bản mở rộng: `expansion/<tên>/{packs,plugins}`; mỗi bản có README riêng.
- Máy chủ plugin trả mọi lỗi dạng JSON; lỗi ngoài dự kiến được ghi nhật ký, không lộ chi tiết.

### Fixed
- Test cài thật chạy trọn một hồ sơ khai sinh của gói Một cửa: quy trình kết thúc bằng thông báo, hồ sơ phải đóng sau khi
  duyệt (B1, cần Desktiny có bản sửa “nhánh quy trình hết bước thì hồ sơ kết thúc”).
- Bước đóng gói kiểm độ dài tiêu đề, mô tả và cấu trúc ô cấu hình như Desktiny (chép `desktiny-plugin` mới vào
  `lib/desktiny_plugin`), nên manifest qua bước đóng gói không còn bị từ chối khi cài.
- Địa chỉ `/cong/` của cổng tiếp nhận chuyển tới trang nộp hồ sơ thay vì báo 404.
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
