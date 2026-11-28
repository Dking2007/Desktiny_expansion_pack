<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Đóng góp

Cảm ơn bạn đã quan tâm tới Desktiny Expansion Pack. Repo này chứa các bản mở rộng cho
[Desktiny](https://github.com/Dking2007/DXOS_Desktiny) (cần Desktiny 3.1.0 trở lên). Xin đọc thêm
[Quy tắc ứng xử](CODE_OF_CONDUCT.md).

## Người duy trì

Mảng phụ trách ghi theo lịch sử commit.

| GitHub | Mảng phụ trách |
|---|---|
| [@Dking2007](https://github.com/Dking2007) | Plugin Cảm biến, Lưu trữ lịch sử; sửa lỗi phân quyền và bảo mật; CI, phát hành |
| [@Mai1174](https://github.com/Mai1174) | Bộ khung máy chủ plugin, gói giao diện và các plugin Nhân sự, Một cửa, Văn thư; đóng gói |
| [@Raphael-Fug](https://github.com/Raphael-Fug) | Giao diện trực quan của plugin; chọn gói khi đóng gói |

## Nguyên tắc bắt buộc

- **Không sửa mã Desktiny.** Bản mở rộng chỉ làm việc qua gói giao diện (dữ liệu thuần) và plugin (khung cách ly hoặc
  máy chủ plugin gọi API Desktiny).
- Plugin chỉ xin **quyền cần dùng**; máy chủ plugin kiểm chữ ký, không tin dữ liệu từ trình duyệt khi chưa kiểm.
- Gói giao diện **không chứa mã chạy được**, không chứa dữ liệu thật của một cơ quan.
- Máy chủ plugin dùng thư viện chuẩn Python, không thêm phụ thuộc pip khi chưa cần (xem `lib/mo_rong`).
- Mọi tệp có `SPDX-License-Identifier` và `SPDX-FileCopyrightText` (hoặc được khai trong `REUSE.toml`).
- Không đưa mật khẩu, token, khóa ký hay dữ liệu cá nhân thật vào mã, tài liệu, ảnh chụp.

## Quy trình

1. **Issue**: [mở issue](https://github.com/Dking2007/Desktiny_expansion_pack/issues/new/choose) (báo lỗi, đề xuất hoặc
   bản mở rộng mới) trước khi làm việc lớn, để thống nhất hướng đi.
2. **Nhánh**: từ `main`, tạo `feat/<số issue>-<mô tả ngắn>`, `fix/<số issue>-<mô tả ngắn>` hoặc
   `docs/<số issue>-<mô tả ngắn>`. Người ngoài nhóm: fork rồi tạo nhánh trong fork.
3. **Môi trường**: Python 3.11+ (CI dùng 3.13), Node 22 cho test trang; `pip install pytest ruff`. Chỉ cần
   `deploy/.env` (sao từ `deploy/.env.example`) khi chạy máy chủ plugin bằng Docker; không commit tệp này.
4. **Sửa và kiểm**:
   ```
   make lint           # ruff
   make test           # máy chủ plugin và đóng gói (Python)
   make test-js        # trang của plugin (Node 22)
   make dist           # đóng gói thử vào dist/
   reuse lint          # khai báo giấy phép
   make test-desktiny DESKTINY_DIR=/đường/dẫn/tới/Desktiny   # cài thật vào một bản Desktiny
   ```
5. **Commit**: theo [Conventional Commits](https://www.conventionalcommits.org/vi) (`feat:`, `fix:`, `docs:`, `test:`,
   `refactor:`, `chore:`), mô tả bằng tiếng Việt, mỗi commit một việc, có số issue khi có.
6. **Pull request**: dùng mẫu có sẵn, mô tả có dòng `Fixes #<số issue>`.

## Yêu cầu với pull request

- Có test đi kèm cho mã mới hoặc lỗi được sửa.
- Thêm một dòng vào mục `[Unreleased]` của [CHANGELOG.md](CHANGELOG.md).
- Tăng `version` trong manifest của gói hoặc plugin có nội dung thay đổi (tên tệp `.zip` lấy theo `version`).
- Đổi giao diện: đính kèm ảnh trước và sau (dữ liệu mẫu giả).
- CI xanh (`make lint`, `make test`, `make test-js`, `make dist`, cài thử vào Desktiny).
- **Người khác duyệt**: ít nhất một người duyệt đồng ý; người viết không tự duyệt.

## Đánh phiên bản và phát hành

- Phiên bản của repo theo [SemVer](https://semver.org/lang/vi/) và **độc lập** với phiên bản Desktiny. Bản Desktiny tối
  thiểu cần có được ghi ở bảng tương thích trong [README](README.md).
- Mỗi gói và mỗi plugin có trường `version` riêng trong manifest. `scripts/kiem_phien_ban.py` kiểm điều này khi phát hành.
- Định dạng manifest (`desktiny-pack/1`, `desktiny-plugin/1`, `desktiny-plugin/2`) chỉ đổi khi có thay đổi phá vỡ
  tương thích.
- Phát hành bằng tag `vX.Y.Z` (workflow `release.yml`). Hiện chưa có bản phát hành; `v1.1.0` là bản dự kiến.

## Giấy phép của phần đóng góp

Đóng góp của bạn được cấp phép theo Apache-2.0 như cả repo (mục 5 của giấy phép). Bạn có thể thêm dòng
`Signed-off-by: Tên <email>` vào commit (`git commit -s`) để xác nhận quyền đóng góp; không bắt buộc.

## Báo lỗi và bảo mật

Lỗi thường: dùng mẫu [báo lỗi](https://github.com/Dking2007/Desktiny_expansion_pack/issues/new/choose). Lỗ hổng bảo
mật: **không** mở issue công khai, xem [SECURITY.md](SECURITY.md).
