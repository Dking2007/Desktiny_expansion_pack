<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Thành phần bên thứ ba

Repo này không có thư viện phụ thuộc nào được cài kèm trong bản phân phối. Phần được sao chép nguyên văn từ bên ngoài:

## Phông chữ (`sdk/phong-chu/`)

| Thành phần | Giấy phép | Nguồn | Tệp |
|---|---|---|---|
| Be Vietnam Pro, © 2021 The Be Vietnam Pro Project Authors | SIL OFL 1.1 ([bản đầy đủ](sdk/phong-chu/OFL-BeVietnamPro.txt)) | https://github.com/bettergui/BeVietnamPro | `be-vietnam-pro-{latin,vietnamese}-{400,600,700}-normal.woff2` |
| Source Sans 3, © 2023 Adobe, tên dành riêng "Source" | SIL OFL 1.1 ([bản đầy đủ](sdk/phong-chu/OFL-SourceSans3.txt)) | https://github.com/adobe-fonts/source-sans | `source-sans-3-{latin,vietnamese}-{400,600}-normal.woff2` |

Các tệp `.woff2` là bản tập con (latin, vietnamese) của phông gốc, giữ nguyên tên tệp theo từng độ đậm. Giấy phép OFL
yêu cầu giữ thông báo bản quyền và không bán riêng phông chữ; hai tệp giấy phép nằm cạnh phông.

## Mã của Desktiny

`lib/desktiny_plugin/` và `sdk/desktiny-plugin-sdk.js` là bản sao SDK của Desktiny
([DXOS_Desktiny](https://github.com/Dking2007/DXOS_Desktiny)), giấy phép Apache-2.0.
