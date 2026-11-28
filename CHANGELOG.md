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
- README của từng bản mở rộng có ảnh bìa (trang đăng nhập và trang chủ theo gói), dòng tóm tắt phiên bản gói, số plugin, phiên bản Desktiny cần, và bộ ảnh màn hình có chú thích (ảnh WebP trong `expansion/<bản>/anh/`, chụp từ bản chạy thử với dữ liệu mẫu).
- Một cửa (1.2.1), Nhân sự (1.2.1), Văn thư (1.1.1): 11 quy trình có nhánh kết thúc bằng "Gửi thông báo" nay có bước Kết thúc rõ ràng, hiện trên canvas và đóng hồ sơ cả trên Desktiny 3.1.0. `dong_goi.py` cảnh báo (không chặn) quy trình có nhánh không có bước Kết thúc.
- Gói giao diện Một cửa (1.2.0), Nhân sự (1.2.0), Văn thư (1.1.0) làm lại cho hài hoà: bảng màu đầy đủ cho cả giao diện sáng và tối (nền, chữ, viền, màu nhấn cùng một sắc, đạt tương phản WCAG AA), logo mới cùng một họ (nền bo tròn chuyển màu, hình trắng, điểm nhấn vàng), nền trang đăng nhập theo màu gói, góc bo theo tính chất từng gói; tiêu đề đăng nhập Văn thư không còn trùng tên ứng dụng. Plugin nhận màu từ Desktiny nên đổi màu theo.
- Bộ giới hạn tần suất `Window` chuyển vào `lib/mo_rong` để các plugin dùng chung.
- Trang đăng nhập Một cửa đổi tiêu đề thành “Cổng làm việc của cán bộ” (không lặp tên ứng dụng).
- Tách theo bản mở rộng: `expansion/<tên>/{packs,plugins}`; mỗi bản có README riêng.
- Máy chủ plugin trả mọi lỗi dạng JSON; lỗi ngoài dự kiến được ghi nhật ký, không lộ chi tiết.
- Trình bày lại README (sơ đồ luồng dữ liệu, thẻ bản mở rộng, bảng công nghệ), thêm README_EN, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT và mẫu issue.

### Fixed
- Bộ giao diện plugin: ở giao diện tối, nút lọc và nút tháng có nền riêng không còn bị tô chữ tối (gần như không đọc được); nút chính vẫn chữ tối trên nền nhấn sáng.
- Ký số: khung đặt mã PIN hiện lúc mở trang không tự đặt focus khi người dùng chưa bấm vào khung (trình duyệt chặn và in cảnh
  báo trên console).
- Khung của plugin co lại vừa nội dung: chép SDK khung mới của Desktiny vào `sdk/` (bản cũ đo `scrollHeight` của `<html>`, giá
  trị không bao giờ nhỏ hơn khung, nên khung chỉ giãn mà không co).
- Sổ tiếp nhận trực tuyến ghi “Chưa trình hồ sơ” (thay cho “Chưa tạo hồ sơ”) khi luồng đã tạo bản nháp nhưng chưa trình:
  plugin chỉ biết hồ sơ khi hồ sơ được trình. Test cài thật kiểm sổ gắn đúng hồ sơ sau khi trình (B8; cần Desktiny có bản
  sửa “hồ sơ do luồng tạo trình được”).
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
