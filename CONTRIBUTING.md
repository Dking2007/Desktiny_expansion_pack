<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Đóng góp

Cảm ơn bạn đã quan tâm tới Desktiny Expansion Pack. Repo này chứa các bản mở rộng cho
[Desktiny](https://github.com/Dking2007/DXOS_Desktiny) (cần Desktiny 3.1.0 trở lên). Xin đọc thêm
[Quy tắc ứng xử](CODE_OF_CONDUCT.md).

## Quy trình

1. **Issue**: mở issue (báo lỗi hoặc đề xuất) trước khi làm việc lớn, để thống nhất hướng đi.
2. **Nhánh**: tạo nhánh `feat/<số issue>-<mô tả ngắn>`, `fix/<số issue>-<mô tả ngắn>` hoặc `docs/<số issue>-<mô tả ngắn>`.
3. **Commit**: theo [Conventional Commits](https://www.conventionalcommits.org/vi) (`feat:`, `fix:`, `docs:`, `test:`,
   `refactor:`, `chore:`), mô tả bằng tiếng Việt, mỗi commit một việc.
4. **Pull request**: mô tả có dòng `Fixes #<số issue>` và thêm một dòng vào mục `[Unreleased]` của
   [CHANGELOG.md](CHANGELOG.md).
5. **Duyệt**: CI xanh (`make lint`, `make test`, `make test-js`, `make dist`) và ít nhất một người duyệt đồng ý.
6. **Gộp** vào `main`.

Tệp mới cần dòng `SPDX-License-Identifier` và `SPDX-FileCopyrightText` như các tệp hiện có (hoặc được khai trong
`REUSE.toml`); kiểm bằng `reuse lint`.

## Chạy kiểm thử

```
make lint           # ruff
make test           # máy chủ plugin (Python)
make test-js        # trang của plugin (Node 22)
make dist           # đóng gói thử vào dist/
make test-desktiny DESKTINY_DIR=/đường/dẫn/tới/Desktiny   # cài thật vào một bản Desktiny
```

## Đánh phiên bản

- Phiên bản của repo theo [SemVer](https://semver.org/lang/vi/) và **độc lập** với phiên bản Desktiny. Bản Desktiny tối
  thiểu cần có được ghi ở bảng tương thích trong [README](README.md).
- Mỗi gói và mỗi plugin có trường `version` riêng trong manifest. Tăng `version` khi nội dung của gói hoặc plugin đó
  thay đổi, vì tên tệp `.zip` lấy theo `version`.
- Định dạng manifest (`desktiny-pack/1`, `desktiny-plugin/1`, `desktiny-plugin/2`) chỉ đổi khi có thay đổi phá vỡ
  tương thích.
