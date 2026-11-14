<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Desktiny Expansion Pack

Bộ mở rộng cho Desktiny: **2 gói giao diện** và **8 plugin** để dùng Desktiny
cho **bộ phận nhân sự của doanh nghiệp** và **bộ phận một cửa của UBND cấp xã**. Gói giao diện không chứa mã; plugin
không chạy mã trong Desktiny (trang chạy trong khung cách ly, máy chủ plugin chạy riêng), đúng mô hình mở rộng của
Desktiny (`desktiny-pack/1`, `desktiny-plugin/1`, `desktiny-plugin/2`).

Cần Desktiny có API plugin bản 2 trở lên (nhánh `feat/plugin-dong-goi`).

## Có gì

### Gói giao diện (`packs/`)

| Gói | Giao diện | Quy trình | Kiến thức cho trợ lý AI |
|---|---|---|---|
| **Nhân sự doanh nghiệp** `vn.mo-rong.nhan-su` | Xanh ngọc, trang đăng nhập riêng, “Hồ sơ” → “Đơn từ” | Đơn nghỉ phép (trên 3 ngày lên Giám đốc), Điều chỉnh công, Làm thêm giờ (trên 4 giờ lên Giám đốc), Đổi ca, Phê duyệt bảng lương, Đánh giá KPI, Gia hạn hợp đồng/giấy tờ | Quy chế chấm công, nghỉ phép, cách tính lương, đánh giá KPI |
| **Một cửa cấp xã** `vn.mo-rong.mot-cua-xa` | Đỏ – vàng, “Hồ sơ” → “Hồ sơ thủ tục” | Đăng ký khai sinh, kết hôn, khai tử; Chứng thực bản sao; Xác nhận tình trạng hôn nhân; Hoà giải ở cơ sở; mẫu “Lấy ý kiến ban, ngành” | Hướng dẫn tiếp nhận, thời hạn giải quyết, hồ sơ nộp trực tuyến |

Biểu mẫu một cửa có sẵn các trường plugin dùng: `ho_ten`, `ngay_sinh`, `so_cccd`, `noi_thuong_tru` (Đọc giấy tờ),
`so_van_ban`, `ngay_van_ban` (Sổ văn bản), `ma_tra_cuu` (Tiếp nhận trực tuyến), `so_ngay_giai_quyet` (Tính hạn).
Biểu mẫu nhân sự có `diem_kpi`, `xep_loai` (Tiền lương và KPI), `ngay_het_han` (Nhắc hạn hồ sơ).

### Plugin (`plugins/`)

| Plugin | Dạng | Làm gì | Gắn vào Desktiny |
|---|---|---|---|
| **Chấm công GPS** `cham-cong` | kết nối, cổng 9201 | Vào/ra ca bằng vị trí GPS trong bán kính trụ sở; ca làm, giờ cho phép muộn; tổng hợp công tháng, xuất CSV | Trang *Chấm công*, khối trang chủ, trang quản trị *Ca làm và địa điểm*; sự kiện **đi muộn quá N lần/tháng**; trợ lý trả lời “tháng này tôi đi muộn mấy lần” |
| **Tiền lương và KPI** `luong-kpi` | kết nối, 9202 | Bậc lương, hồ sơ lương, tính lương tháng (ngày công từ Chấm công, bảo hiểm, thuế TNCN lũy tiến), chốt kỳ, phiếu lương; chấm KPI theo tiêu chí có trọng số | Bước quy trình chạy lâu **Chốt kỳ lương**; trang *Phiếu lương*; tab *Chấm điểm KPI* trong hồ sơ (ghi điểm, xếp loại vào hồ sơ); trợ lý đọc phiếu lương |
| **Sổ văn bản** `so-van-ban` | kết nối, 9203 | Sổ theo loại văn bản, số liên tục theo năm, không nhảy số, không trùng; số huỷ vẫn giữ | Bước **Cấp số văn bản**; nút *Cấp số văn bản* trên hồ sơ (ghi số, ngày vào hồ sơ); tab *Số văn bản*; trang *Sổ văn bản* |
| **Ký số văn bản** `ky-so` | kết nối, 9204 | Ký tài liệu của hồ sơ bằng PIN cá nhân, gắn phiếu xác nhận (PDF) có mã; trang công khai kiểm mã | Bước chạy lâu **Ký số văn bản** (chờ người ký); trang *Văn bản chờ ký*; nút *Ký số* |
| **Nhắc hạn hồ sơ** `nhac-han` | kết nối, 9205 | Theo dõi trường ngày hết hạn (hợp đồng, giấy phép…) trong hồ sơ của quy trình được chọn; nhắc trước 30/7/1 ngày và đúng ngày | Sự kiện **sắp hết hạn**; khối trang chủ; trang quản trị; trợ lý liệt kê hồ sơ sắp hết hạn |
| **Tiếp nhận trực tuyến** `tiep-nhan` | kết nối, 9206 | Trang công khai nộp yêu cầu và tra cứu tình trạng bằng mã tra cứu + mã bí mật (không cần tài khoản); nhận hồ sơ từ hệ thống ngoài bằng khoá | Sự kiện **có yêu cầu nộp trực tuyến** để luồng tạo hồ sơ; cập nhật tình trạng theo sự kiện của hồ sơ; khung trên hồ sơ |
| **Tính hạn theo ngày làm việc** `tinh-han` | đóng gói (không máy chủ) | Tính hạn bỏ cuối tuần, ngày lễ, tính ngày làm bù | Trang *Tính hạn giải quyết*; khung *Hạn giải quyết* trên hồ sơ |
| **Đọc giấy tờ, điền sẵn** `doc-giay-to` | đóng gói | Đọc lớp chữ của tài liệu đã nộp (văn bản, PDF có chữ) hoặc nội dung dán vào, nhận ra họ tên, ngày sinh, số định danh, quê quán, nơi thường trú, MST, điện thoại | Nút *Đọc giấy tờ* trên hồ sơ: cán bộ xem, sửa, xác nhận rồi ghi vào hồ sơ |

## Cài đặt

### 1. Đóng gói

```sh
make dist                       # hoặc: python3 scripts/dong_goi.py
make dist HOST=plugins.co-quan.vn   # đổi base_url của plugin kết nối sang máy chủ thật
```

Kết quả trong `dist/`: `goi-*.zip` (gói giao diện), `plugin-tinh-han.zip`, `plugin-doc-giay-to.zip` (plugin đóng gói),
`plugin-*.json` (manifest plugin kết nối).

### 2. Gói giao diện

**Quản trị › Gói giao diện › Tải gói lên** → chọn `dist/goi-nhan-su.zip` hoặc `dist/goi-mot-cua-xa.zip` → xem trước →
cài → **Dùng giao diện này**. Cài gói cần quyền quản lý biểu mẫu và trợ lý AI.

### 3. Plugin đóng gói

**Quản trị › Plugin › Cài plugin** → chọn `dist/plugin-tinh-han.zip` / `dist/plugin-doc-giay-to.zip` → **Duyệt quyền**.
Không cần máy chủ. Đọc giấy tờ cần duyệt đủ các trường được ghi.

### 4. Plugin kết nối

1. Chạy máy chủ: `cp deploy/.env.example deploy/.env`, đặt `DESKTINY_URL`, rồi `make up` (Docker Compose, một image
   cho cả 6 plugin, dữ liệu SQLite trong volume riêng của từng plugin).
2. Trong cấu hình Desktiny: thêm máy chủ plugin vào `PLUGIN_ALLOWED_HOSTS` (ví dụ `plugins.co-quan.vn`) và origin
   vào `PLUGIN_FRAME_SOURCES` (ví dụ `https://plugins.co-quan.vn`).
3. **Quản trị › Plugin › Cài plugin** → chọn `dist/plugin-<tên>.json` → **Duyệt quyền**. Desktiny hiện **token** và
   **khoá ký** một lần: chép vào `deploy/.env` (`<TÊN>_TOKEN`, `<TÊN>_SECRET`) rồi `make up` lại.
4. **Cấu hình** từng plugin ở trang Plugin:
   - Ký số: **khoá ký của cơ quan** (bắt buộc, chuỗi ngẫu nhiên dài).
   - Chấm công: số lần đi muộn thì báo, sai số GPS tối đa, khoá chia sẻ công (đặt giống ở Tiền lương và KPI).
   - Tiền lương và KPI: lương cơ sở, tỉ lệ bảo hiểm, giảm trừ, biểu thuế, địa chỉ plugin Chấm công và khoá chia sẻ.
   - Sổ văn bản: ký hiệu cơ quan. Nhắc hạn: mã trường ngày hết hạn, mốc nhắc. Tiếp nhận: tên cơ quan, danh sách thủ
     tục, khoá cho hệ thống ngoài.
5. Plugin có trang quản trị (Chấm công, Tiền lương và KPI, Sổ văn bản, Nhắc hạn, Tiếp nhận) mở từ nút tương ứng trên
   dòng plugin. Nhắc hạn cần chọn **quy trình được liệt kê** khi duyệt (ví dụ “Gia hạn hợp đồng, giấy tờ”).
6. Trang công khai của Tiếp nhận trực tuyến (`/cong/nop.html`, `/cong/tra-cuu.html` trên máy chủ plugin 9206) và
   trang kiểm mã ký số (`/cong/xac-thuc.html` trên 9204) cần mở ra Internet qua reverse proxy; phần còn lại của máy
   chủ plugin chỉ cần Desktiny gọi tới được.

### 5. Luồng gợi ý (dựng trên trình thiết kế quy trình)

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
  mỗi địa chỉ; trang tra cứu không hiện nội dung hồ sơ.

## Giới hạn

- **Ký số là mô phỏng** (HMAC bằng khoá của cơ quan) để chạy trọn quy trình; muốn có giá trị pháp lý phải thay
  `Signer` trong `plugins/ky-so/server.py` bằng chữ ký từ chứng thư số của tổ chức cung cấp dịch vụ được cấp phép.
- **Đọc giấy tờ** chỉ đọc lớp chữ (tệp văn bản, PDF có chữ); ảnh quét cần ứng dụng quét có nhận dạng chữ rồi dán
  nội dung vào. Mọi giá trị cần cán bộ kiểm trước khi ghi.
- **Lương**: mức lương cơ sở, tỉ lệ bảo hiểm, giảm trừ gia cảnh, biểu thuế mặc định chỉ để thử; bộ phận nhân sự đặt
  lại theo quy định hiện hành ở **Cấu hình**.
- **Ngày lễ** (`plugins/tinh-han/ui/ngay-lam-viec.js`) và thời hạn thủ tục chỉ là mặc định; sửa theo thông báo nghỉ
  lễ hằng năm và bộ thủ tục hành chính đang áp dụng rồi đóng gói lại. Nội dung kiến thức trong gói là mẫu, cần đối
  chiếu văn bản hiện hành.
- Khung plugin không có hộp thoại `alert/prompt` và không tải tệp về (giới hạn sandbox của Desktiny): CSV hiện trong
  ô để sao chép, xác nhận dùng hộp thoại của Desktiny.
- Với Desktiny hiện tại, hồ sơ do bước **Tạo hồ sơ** của luồng tạo ra chưa được chủ hồ sơ trình (Core chưa cấp quyền
  bản ghi nội dung cho người đó); cần sửa ở Desktiny trước khi dùng luồng “Hồ sơ từ cổng trực tuyến” trọn vẹn.

## Phát triển

```
lib/mo_rong/        bộ khung máy chủ plugin (định tuyến, kiểm chữ ký, phiên người xem, SQLite, PDF)
lib/desktiny_plugin bản sao SDK Python của Desktiny (packages/desktiny-plugin)
sdk/                SDK khung của Desktiny, mo-rong.js (gọi máy chủ plugin bằng phiên), chung.css
packs/  plugins/    gói giao diện, plugin (mỗi plugin: desktiny-plugin.json, server.py, ui/)
scripts/dong_goi.py đóng gói vào dist/
tests/              test máy chủ plugin (Desktiny giả), tests/js (Node), tests/desktiny (cài vào Desktiny thật)
deploy/             Dockerfile, Docker Compose
```

```sh
make test          # Python 3.11+, pytest
make test-js       # Node 22
make test-desktiny   # (Desktiny là thư mục cha) cài mọi gói và plugin vào Desktiny thật (bộ test của Desktiny), chạy luồng qua máy chủ plugin
make lint
```

Mỗi plugin chạy riêng: `PYTHONPATH=lib DESKTINY_URL=… DESKTINY_TOKEN=… DESKTINY_SECRET=… python plugins/cham-cong/server.py`.
Thử nhanh với Desktiny giả: `PYTHONPATH=lib python -m desktiny_plugin.cli dev step cap_so_van_ban --secret … --manifest plugins/so-van-ban/desktiny-plugin.json`.

Giấy phép Apache-2.0.
