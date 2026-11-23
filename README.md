<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Desktiny Expansion Pack

Bộ mở rộng cho Desktiny, gồm **2 gói giao diện** và **8 plugin**, để dùng Desktiny cho:

- **Bộ phận nhân sự của doanh nghiệp**: chấm công GPS, tính lương và KPI, đơn từ, nhắc hạn hợp đồng.
- **Bộ phận một cửa của UBND cấp xã**: thủ tục hộ tịch, chứng thực, sổ văn bản, ký số, tiếp nhận trực tuyến, tính hạn.

Mọi thứ cài vào Desktiny qua giao diện quản trị bằng tệp **.zip**: chỉ cần **bấm đúp `build.bat`** (Windows) để tạo
các tệp đó.

## Mục lục

1. [Cách hoạt động](#cách-hoạt-động)
2. [Đóng gói (build)](#đóng-gói-build)
3. [Cài đặt vào Desktiny](#cài-đặt-vào-desktiny)
4. [Có gì trong bộ mở rộng](#có-gì-trong-bộ-mở-rộng)
5. [Luồng gợi ý](#luồng-gợi-ý)
6. [An toàn](#an-toàn)
7. [Giới hạn](#giới-hạn)
8. [Phát triển](#phát-triển)

## Cách hoạt động

Bộ mở rộng không sửa mã của Desktiny; nó dùng đúng mô hình mở rộng của Desktiny (`desktiny-pack/1`,
`desktiny-plugin/1`, `desktiny-plugin/2`).

Mã nguồn chia theo **bản mở rộng**: mỗi bản mở rộng là một thư mục trong `expansion/`, chứa các gói giao diện
(`packs/`) và plugin (`plugins/`) dùng cho đúng nghiệp vụ đó:

```
expansion/
├── nhan-su/                    Nhân sự doanh nghiệp
│   ├── packs/nhan-su/
│   └── plugins/cham-cong/  luong-kpi/  nhac-han/
└── mot-cua-xa/                 Một cửa cấp xã
    ├── packs/mot-cua-xa/
    └── plugins/so-van-ban/  ky-so/  tiep-nhan/  tinh-han/  doc-giay-to/
```

Có ba loại thành phần:

| Thành phần | Là gì | Cần máy chủ riêng? |
|---|---|---|
| **Gói giao diện** (`packs/`) | Dữ liệu thuần: màu sắc, logo, trang đăng nhập, từ ngữ, quy trình và biểu mẫu, kiến thức cho trợ lý AI | Không |
| **Plugin đóng gói** (`tinh-han`, `doc-giay-to`) | Trang web chạy trong khung cách ly của Desktiny, tính toán ngay trên trình duyệt | Không |
| **Plugin kết nối** (6 plugin còn lại) | Trang web + máy chủ riêng (Python, SQLite). Desktiny gọi máy chủ khi có sự kiện, bước quy trình, câu hỏi của trợ lý; trang plugin gọi máy chủ bằng phiên của người đang xem | Có — chạy bằng Docker Compose |

```
                 ┌──────────── Desktiny ────────────┐
 người dùng ───▶ │ giao diện (gói)  khung plugin ◀──┼── trang plugin (ui/)
                 │ quy trình, sự kiện, trợ lý AI ───┼──▶ máy chủ plugin kết nối (cổng 9201–9206)
                 └──────────────────────────────────┘          ▲
 người dân ──────────────── trang công khai (nộp, tra cứu, kiểm mã ký) ──┘
```

**Yêu cầu:** Desktiny có API plugin bản 2 trở lên (nhánh `feat/plugin-dong-goi`). Đóng gói cần **Python 3.11+**.
Máy chủ plugin kết nối cần **Docker** (hoặc Python 3.11+ chạy trực tiếp).

## Đóng gói (build)

Chọn một cách:

| Cách | Lệnh |
|---|---|
| Windows | **Bấm đúp `build.bat`** → chọn từ danh sách (Enter = tất cả); xong sẽ mở thư mục `dist` |
| VS Code | **Ctrl+Shift+B** → “Đóng gói (dist/*.zip)” |
| Dòng lệnh | `python scripts/dong_goi.py` · `./build.sh` · `make build` |

### Chọn gói, plugin cần đóng gói

Bấm đúp `build.bat` sẽ hiện danh sách đánh số theo từng bản mở rộng. Gõ số hoặc tên, cách nhau bởi dấu cách; **Enter**
không gõ gì là đóng gói tất cả:

```
  Bản mở rộng mot-cua-xa  (gõ “mot-cua-xa” để lấy cả bản)
    1. Một cửa cấp xã  [gói giao diện, mot-cua-xa]
    2. Đọc giấy tờ, điền sẵn hồ sơ  [plugin đóng gói, doc-giay-to]
    …
Nhập số hoặc tên, cách nhau bởi dấu cách (Enter = tất cả): 1 2 ky-so
```

Từ dòng lệnh, ghi tên sau lệnh (không ghi gì = tất cả):

```sh
build.bat nhan-su                  # cả bản mở rộng Nhân sự: gói + 3 plugin
build.bat ky-so so-van-ban         # chỉ hai plugin
build.bat goi-nhan-su              # chỉ gói giao diện (tên bản mở rộng trùng tên gói thì thêm goi-)
python scripts/dong_goi.py --chon  # hiện danh sách như khi bấm đúp
make build CHON="nhan-su ky-so"
```

Tên là tên thư mục của bản mở rộng, gói hoặc plugin (`plugin-<tên>` cũng được). Gói máy chủ chỉ chứa các plugin kết
nối được chọn, và `HUONG-DAN-CAI.txt` ghi đúng lệnh `docker compose … up -d <các plugin đó>`. Chỉ chọn gói giao diện
và plugin đóng gói thì không có gói máy chủ.

### Đóng gói cho máy chủ thật

Khi triển khai thật, chỉ cho plugin kết nối biết máy chủ của chúng ở đâu:

```sh
build.bat --host plugins.co-quan.vn        # hoặc: python scripts/dong_goi.py --host plugins.co-quan.vn
                                           #       make build HOST=plugins.co-quan.vn
```

`--host` có dấu chấm (tên miền, IP) → `base_url` thành `https://<host>/<tên-plugin>` (đặt sau reverse proxy); tên máy
không có dấu chấm → `http://<host>:<cổng>`. Không có `--host`, `base_url` là `http://localhost:92xx` (để thử trên một máy).

Trước khi ghi, bước đóng gói **kiểm mọi manifest** theo quy tắc Desktiny áp dụng khi tải lên, và kiểm mọi tệp gói giao
diện trỏ tới (logo, quy trình, mẫu, kiến thức) có thật và đúng JSON. Có lỗi thì báo rõ tệp nào, không ghi gì cả.

### Kết quả trong `dist/`

`dist/` được làm trống rồi ghi lại mỗi lần đóng gói (chỉ còn những gì vừa chọn). Mỗi bản mở rộng một thư mục, cài thư mục nào thì lấy đủ tệp ở đó:

```
dist/
├── HUONG-DAN-CAI.txt                       tệp nào tải lên đâu, theo thứ tự
├── nhan-su/
│   ├── goi-nhan-su-1.1.0.zip               gói giao diện
│   ├── plugin-cham-cong-1.0.0.zip          plugin kết nối: chỉ manifest (trang do máy chủ plugin phục vụ)
│   ├── plugin-luong-kpi-1.0.0.zip
│   └── plugin-nhac-han-1.0.0.zip
├── mot-cua-xa/
│   ├── goi-mot-cua-xa-1.1.0.zip
│   ├── plugin-tinh-han-1.0.0.zip           plugin đóng gói: manifest + trang + SDK khung
│   ├── plugin-doc-giay-to-1.0.0.zip
│   └── plugin-so-van-ban-1.0.0.zip, plugin-ky-so-1.0.0.zip, plugin-tiep-nhan-1.0.0.zip
└── may-chu-plugin/
    └── may-chu-plugin-1.0.0.zip            mã máy chủ 6 plugin kết nối + Dockerfile + compose.yaml
```

Đóng gói tất cả thì gói máy chủ chứa cả 6 plugin kết nối; chọn riêng một bản mở rộng thì chỉ chứa plugin của bản đó.

Tên tệp có phiên bản lấy từ manifest (`version`). Cùng mã nguồn luôn cho ra cùng tệp .zip.

## Cài đặt vào Desktiny

### Bước 1. Gói giao diện

**Quản trị › Gói giao diện › Tải gói lên** → chọn `goi-*.zip` trong `dist/<bản mở rộng>/` → xem trước → cài → **Dùng giao
diện này**. Cài gói cần quyền quản lý biểu mẫu và trợ lý AI. Cài cả hai gói được; chỉ một gói là giao diện đang dùng.

### Bước 2. Plugin đóng gói

**Quản trị › Plugin › Cài plugin** → chọn `plugin-tinh-han-*.zip` / `plugin-doc-giay-to-*.zip` → **Duyệt quyền**.
Không cần máy chủ. Đọc giấy tờ cần duyệt đủ các trường được ghi.

### Bước 3. Máy chủ plugin kết nối

1. Chép `dist/may-chu-plugin/may-chu-plugin-*.zip` lên máy chủ, giải nén.
2. `cp deploy/.env.example deploy/.env`, đặt `DESKTINY_URL` (địa chỉ máy chủ plugin gọi tới Desktiny).
3. `docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build` (trong mã nguồn: `make up`).
   Một image cho cả 6 plugin; dữ liệu SQLite nằm trong volume riêng của từng plugin.
4. Trong cấu hình Desktiny: thêm máy chủ plugin vào `PLUGIN_ALLOWED_HOSTS` (ví dụ `plugins.co-quan.vn`) và origin
   vào `PLUGIN_FRAME_SOURCES` (ví dụ `https://plugins.co-quan.vn`).

| Plugin | Cổng | Biến trong `deploy/.env` |
|---|---|---|
| Chấm công GPS | 9201 | `CHAM_CONG_TOKEN`, `CHAM_CONG_SECRET` |
| Tiền lương và KPI | 9202 | `LUONG_KPI_TOKEN`, `LUONG_KPI_SECRET` |
| Sổ văn bản | 9203 | `SO_VAN_BAN_TOKEN`, `SO_VAN_BAN_SECRET` |
| Ký số văn bản | 9204 | `KY_SO_TOKEN`, `KY_SO_SECRET` |
| Nhắc hạn hồ sơ | 9205 | `NHAC_HAN_TOKEN`, `NHAC_HAN_SECRET` |
| Tiếp nhận trực tuyến | 9206 | `TIEP_NHAN_TOKEN`, `TIEP_NHAN_SECRET` |

Với `--host` là tên miền, reverse proxy cần chuyển `https://<host>/<tên-plugin>/…` tới cổng tương ứng.

### Bước 4. Cài plugin kết nối

1. **Quản trị › Plugin › Cài plugin** → chọn `plugin-<tên>-*.zip` → **Duyệt quyền**.
2. Desktiny hiện **token** và **khoá ký** một lần: chép vào `deploy/.env` (`<TÊN>_TOKEN`, `<TÊN>_SECRET`) rồi chạy
   lại `docker compose … up -d`.
3. Nhắc hạn cần chọn **quy trình được liệt kê** khi duyệt (ví dụ “Gia hạn hợp đồng, giấy tờ”).

### Bước 5. Cấu hình

Ở trang **Plugin**, nút **Cấu hình** của từng plugin:

- **Ký số**: khoá ký của cơ quan (bắt buộc, chuỗi ngẫu nhiên dài).
- **Chấm công**: số lần đi muộn thì báo, sai số GPS tối đa, khoá chia sẻ công (đặt giống ở Tiền lương và KPI).
- **Tiền lương và KPI**: lương cơ sở, tỉ lệ bảo hiểm, giảm trừ, biểu thuế, địa chỉ plugin Chấm công và khoá chia sẻ.
- **Sổ văn bản**: ký hiệu cơ quan. **Nhắc hạn**: mã trường ngày hết hạn, mốc nhắc. **Tiếp nhận**: tên cơ quan,
  danh sách thủ tục, khoá cho hệ thống ngoài.

Plugin có trang quản trị (Chấm công, Tiền lương và KPI, Sổ văn bản, Nhắc hạn, Tiếp nhận) mở từ nút tương ứng trên dòng
plugin.

### Bước 6. Trang công khai

Trang của Tiếp nhận trực tuyến (`/cong/nop.html`, `/cong/tra-cuu.html`, cổng 9206) và trang kiểm mã ký số
(`/cong/xac-thuc.html`, cổng 9204) cần mở ra Internet qua reverse proxy. Phần còn lại của máy chủ plugin chỉ cần
Desktiny gọi tới được.

## Có gì trong bộ mở rộng

### Gói giao diện

| Gói | Giao diện | Quy trình | Luồng tự động (cài ở trạng thái tắt) | Kiến thức cho trợ lý AI |
|---|---|---|---|---|
| **Nhân sự doanh nghiệp** `vn.mo-rong.nhan-su` | Xanh ngọc, trang đăng nhập riêng, “Hồ sơ” → “Đơn từ” | Đơn nghỉ phép (trên 3 ngày lên Giám đốc), Điều chỉnh công, Làm thêm giờ (trên 4 giờ lên Giám đốc), Đổi ca, Phê duyệt bảng lương, Đánh giá KPI, Gia hạn hợp đồng/giấy tờ | Nhắc đơn bị trả lại chưa bổ sung sau 1 ngày; Cảnh báo đơn quá hạn; Báo công việc quá hạn | Quy chế chấm công, nghỉ phép, cách tính lương, đánh giá KPI |
| **Một cửa cấp xã** `vn.mo-rong.mot-cua-xa` | Đỏ – vàng, “Hồ sơ” → “Hồ sơ thủ tục” | Đăng ký khai sinh, kết hôn, khai tử; Chứng thực bản sao; Xác nhận tình trạng hôn nhân; Hoà giải ở cơ sở; mẫu “Lấy ý kiến ban, ngành” | Nhắc hồ sơ bị trả lại chưa bổ sung sau 1 ngày; Cảnh báo hồ sơ quá hạn; Báo lãnh đạo khi hồ sơ bị từ chối | Hướng dẫn tiếp nhận, thời hạn giải quyết, hồ sơ nộp trực tuyến |

Biểu mẫu có sẵn các trường plugin dùng (đổi mã trường thì phải đổi cả plugin):

| Gói | Trường | Plugin dùng |
|---|---|---|
| Một cửa | `ho_ten`, `ngay_sinh`, `so_cccd`, `noi_thuong_tru` | Đọc giấy tờ |
| Một cửa | `so_van_ban`, `ngay_van_ban` | Sổ văn bản |
| Một cửa | `ma_tra_cuu` | Tiếp nhận trực tuyến |
| Một cửa | `so_ngay_giai_quyet` | Tính hạn |
| Nhân sự | `diem_kpi`, `xep_loai` | Tiền lương và KPI |
| Nhân sự | `ngay_het_han` | Nhắc hạn hồ sơ |

### Plugin

| Plugin | Dạng | Làm gì | Gắn vào Desktiny |
|---|---|---|---|
| **Chấm công GPS** `cham-cong` | kết nối, 9201 | Vào/ra ca bằng vị trí GPS trong bán kính trụ sở; ca làm, giờ cho phép muộn; tổng hợp công tháng, xuất CSV | Trang *Chấm công*, khối trang chủ, trang quản trị *Ca làm và địa điểm*; sự kiện **đi muộn quá N lần/tháng**; trợ lý trả lời “tháng này tôi đi muộn mấy lần” |
| **Tiền lương và KPI** `luong-kpi` | kết nối, 9202 | Bậc lương, hồ sơ lương, tính lương tháng (ngày công từ Chấm công, bảo hiểm, thuế TNCN lũy tiến), chốt kỳ, phiếu lương; chấm KPI theo tiêu chí có trọng số | Bước quy trình chạy lâu **Chốt kỳ lương**; trang *Phiếu lương*; tab *Chấm điểm KPI* trong hồ sơ (ghi điểm, xếp loại vào hồ sơ); trợ lý đọc phiếu lương |
| **Sổ văn bản** `so-van-ban` | kết nối, 9203 | Sổ theo loại văn bản, số liên tục theo năm, không nhảy số, không trùng; số huỷ vẫn giữ | Bước **Cấp số văn bản**; nút *Cấp số văn bản* trên hồ sơ (ghi số, ngày vào hồ sơ); tab *Số văn bản*; trang *Sổ văn bản* |
| **Ký số văn bản** `ky-so` | kết nối, 9204 | Ký tài liệu của hồ sơ bằng PIN cá nhân, gắn phiếu xác nhận (PDF) có mã; trang công khai kiểm mã | Bước chạy lâu **Ký số văn bản** (chờ người ký); trang *Văn bản chờ ký*; nút *Ký số* |
| **Nhắc hạn hồ sơ** `nhac-han` | kết nối, 9205 | Theo dõi trường ngày hết hạn (hợp đồng, giấy phép…) trong hồ sơ của quy trình được chọn; nhắc trước 30/7/1 ngày và đúng ngày | Sự kiện **sắp hết hạn**; khối trang chủ; trang quản trị; trợ lý liệt kê hồ sơ sắp hết hạn |
| **Tiếp nhận trực tuyến** `tiep-nhan` | kết nối, 9206 | Trang công khai nộp yêu cầu và tra cứu tình trạng bằng mã tra cứu + mã bí mật (không cần tài khoản); nhận hồ sơ từ hệ thống ngoài bằng khoá | Sự kiện **có yêu cầu nộp trực tuyến** để luồng tạo hồ sơ; cập nhật tình trạng theo sự kiện của hồ sơ; khung trên hồ sơ |
| **Tính hạn theo ngày làm việc** `tinh-han` | đóng gói | Tính hạn bỏ cuối tuần, ngày lễ, tính ngày làm bù | Trang *Tính hạn giải quyết*; khung *Hạn giải quyết* trên hồ sơ |
| **Đọc giấy tờ, điền sẵn** `doc-giay-to` | đóng gói | Đọc lớp chữ của tài liệu đã nộp (văn bản, PDF có chữ) hoặc nội dung dán vào, nhận ra họ tên, ngày sinh, số định danh, quê quán, nơi thường trú, MST, điện thoại | Nút *Đọc giấy tờ* trên hồ sơ: cán bộ xem, sửa, xác nhận rồi ghi vào hồ sơ |

Các luồng tự động dùng sự kiện có sẵn của Desktiny nên chạy được cả khi chưa cài plugin; bật ở **Quy trình nghiệp
vụ** sau khi xem lại người nhận.

Plugin nên dùng cùng gói: **Nhân sự** ↔ Chấm công, Tiền lương và KPI, Nhắc hạn. **Một cửa** ↔ Sổ văn bản, Ký số,
Tiếp nhận, Tính hạn, Đọc giấy tờ.

## Luồng gợi ý

Dựng trên trình thiết kế quy trình của Desktiny sau khi cài:

| Mục đích | Bắt đầu | Các bước |
|---|---|---|
| Hồ sơ từ cổng trực tuyến | Sự kiện *Tiếp nhận trực tuyến: Có yêu cầu nộp trực tuyến* | **Tạo hồ sơ** theo biểu mẫu thủ tục, trường `ma_tra_cuu` = `{trigger.ma_tra_cuu}`, `ho_ten` = `{trigger.ho_ten}`… |
| Trả kết quả một cửa | Gắn vào quy trình thủ tục | Sau bước lãnh đạo: **Cấp số văn bản** (sổ `GXN`) → **Ký số văn bản** → thông báo `Số {cap_so.so_van_ban}` |
| Bảng lương tháng | Quy trình “Phê duyệt bảng lương tháng” | Thêm **Chốt kỳ lương** (`ky` = `{form.ky_luong}`) trước bước trưởng bộ phận |
| Gia hạn hợp đồng | Sự kiện *Nhắc hạn hồ sơ: Hồ sơ sắp hết hạn* | **Giao việc** cho bộ phận nhân sự: “Chuẩn bị gia hạn” |
| Kỷ luật lao động | Sự kiện *Chấm công GPS: Đi muộn quá số lần cho phép* | **Thông báo** quản lý trực tiếp |

## An toàn

- Plugin chỉ có những quyền quản trị viên duyệt; token cài đặt chỉ tới hồ sơ plugin được báo hoặc quy trình được chọn.
- Trang của plugin chạy trong khung cách ly; máy chủ plugin xác định người đang xem bằng **token phiên** của Desktiny
  (`GET /plugin/v1/me`), trang quản trị chỉ nhận phiên từ khung `admin.page` (chỉ người quản lý tổ chức mở được).
- Mọi lời Desktiny gọi tới (sự kiện, bước, công cụ trợ lý) được kiểm **chữ ký HMAC**; báo kết quả bước chạy lâu
  cũng được ký.
- Mã PIN ký số lưu dạng PBKDF2, khoá sau 5 lần sai. Trang nộp công khai có câu hỏi kiểm tra và giới hạn 5 lần/giờ
  mỗi địa chỉ; trang tra cứu không hiện nội dung hồ sơ. Địa chỉ lấy từ kết nối; chỉ khi máy chủ đặt sau reverse
  proxy mới bật `TIEP_NHAN_TRUST_PROXY=1` để đọc `X-Forwarded-For` (lấy địa chỉ proxy ghi cuối cùng).
- Sổ văn bản: người dùng chỉ thấy số của hồ sơ họ mở được và số họ tự cấp; cả sổ chỉ xem ở trang quản trị.
- Máy chủ plugin trả mọi lỗi dạng JSON; lỗi ngoài dự kiến ghi vào nhật ký của container, không lộ chi tiết ra trang.
- Container máy chủ plugin chạy bằng người dùng thường, hệ tệp chỉ đọc, `no-new-privileges`. Gói máy chủ không bao
  giờ chứa `deploy/.env`.

## Giới hạn

- **Ký số là mô phỏng** (HMAC bằng khoá của cơ quan) để chạy trọn quy trình; muốn có giá trị pháp lý phải thay
  `Signer` trong `expansion/mot-cua-xa/plugins/ky-so/server.py` bằng chữ ký từ chứng thư số của tổ chức cung cấp dịch vụ được cấp phép.
- **Đọc giấy tờ** chỉ đọc lớp chữ (tệp văn bản, PDF có chữ); ảnh quét cần ứng dụng quét có nhận dạng chữ rồi dán
  nội dung vào. Mọi giá trị cần cán bộ kiểm trước khi ghi.
- **Lương**: mức lương cơ sở, tỉ lệ bảo hiểm, giảm trừ gia cảnh, biểu thuế mặc định chỉ để thử; bộ phận nhân sự đặt
  lại theo quy định hiện hành ở **Cấu hình**.
- **Ngày lễ** (`expansion/mot-cua-xa/plugins/tinh-han/ui/ngay-lam-viec.js`) và thời hạn thủ tục chỉ là mặc định; sửa theo thông báo nghỉ
  lễ hằng năm và bộ thủ tục hành chính đang áp dụng rồi đóng gói lại. Nội dung kiến thức trong gói là mẫu, cần đối
  chiếu văn bản hiện hành.
- Khung plugin không có hộp thoại `alert/prompt` và không tải tệp về (giới hạn sandbox của Desktiny): CSV hiện trong
  ô để sao chép, xác nhận dùng hộp thoại của Desktiny.
- Với Desktiny hiện tại, hồ sơ do bước **Tạo hồ sơ** của luồng tạo ra chưa được chủ hồ sơ trình (Core chưa cấp quyền
  bản ghi nội dung cho người đó); cần sửa ở Desktiny trước khi dùng luồng “Hồ sơ từ cổng trực tuyến” trọn vẹn.

## Phát triển

### Cấu trúc thư mục

```
build.bat, build.sh     nút đóng gói (gọi scripts/dong_goi.py)
scripts/dong_goi.py     kiểm manifest rồi đóng gói vào dist/
expansion/<bản mở rộng>/
  packs/<tên>/          gói giao diện: desktiny-pack.json, assets/, processes/, templates/, knowledge/
  plugins/<tên>/        plugin: desktiny-plugin.json, ui/ (trang), server.py (plugin kết nối), cong/ (trang công khai)
lib/mo_rong/            bộ khung máy chủ plugin (định tuyến, kiểm chữ ký, phiên người xem, SQLite, PDF)
lib/desktiny_plugin/    bản sao SDK Python của Desktiny (packages/desktiny-plugin) — cập nhật cùng Desktiny
sdk/                    SDK khung của Desktiny, mo-rong.js (trang gọi máy chủ plugin bằng phiên), chung.css
tests/                  test máy chủ plugin (Desktiny giả), test đóng gói, tests/js (Node), tests/desktiny (Desktiny thật)
deploy/                 Dockerfile, compose.yaml, .env.example
```

### Thêm bản mở rộng, gói hoặc plugin

Bước đóng gói tự tìm: mọi thư mục `expansion/*/packs/*` có `desktiny-pack.json`, mọi thư mục `expansion/*/plugins/*` có
`desktiny-plugin.json`. Bản mở rộng mới chỉ cần một thư mục mới `expansion/<tên>/` với `packs/` và/hoặc `plugins/`;
`dist/<tên>/` tự xuất hiện. Tên gói và tên plugin không được trùng giữa các bản mở rộng. Manifest có `base_url` là plugin kết nối, không có là plugin đóng gói. Plugin kết nối mới cần thêm `server.py` (theo
mẫu `build(settings) -> App` của plugin có sẵn), một dịch vụ trong `deploy/compose.yaml` và cặp biến trong
`deploy/.env.example`; cổng ở `base_url`, `server.py` và `compose.yaml` phải trùng nhau.

### Kiểm thử

```sh
make test            # test máy chủ plugin và đóng gói (Python 3.11+, pytest)
make test-js         # test mã trang của plugin đóng gói (Node 22)
make test-desktiny   # cài mọi gói và plugin vào Desktiny thật (DESKTINY_DIR, mặc định thư mục cha) rồi chạy luồng
make lint            # ruff
```

Không có `make` (Windows): `set PYTHONPATH=lib` rồi `python -m pytest -q tests --ignore=tests/desktiny`;
`node --test tests/js/*.test.mjs`. Trong VS Code: tác vụ “Kiểm thử”. CI chạy lint, test, test-js và đóng gói.

### Chạy thử một plugin

```sh
PYTHONPATH=lib DESKTINY_URL=… DESKTINY_TOKEN=… DESKTINY_SECRET=… python expansion/nhan-su/plugins/cham-cong/server.py
PYTHONPATH=lib python -m desktiny_plugin.cli dev step cap_so_van_ban --secret … --manifest expansion/mot-cua-xa/plugins/so-van-ban/desktiny-plugin.json
```

Lệnh thứ hai đóng vai Desktiny: ký và gửi một lời gọi bước quy trình tới máy chủ plugin đang chạy.

## Giấy phép

Apache-2.0 (`LICENSE`).
