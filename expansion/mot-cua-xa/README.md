<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Bản mẫu: Một cửa cấp xã

Bản mở rộng mẫu cho **bộ phận một cửa của UBND cấp xã**. Bản này lo trọn đường đi của một hồ sơ thủ tục:
- người dân nộp trực tuyến hoặc tại quầy;
- cán bộ đọc giấy tờ để điền sẵn hồ sơ;
- tự tính hạn theo ngày làm việc;
- lãnh đạo duyệt;
- cấp số văn bản và ký số;
- người dân tra cứu kết quả và kiểm tra mã ký.

Đây là **bản mẫu**: các thủ tục, thời hạn và ngày lễ chỉ là mặc định, còn ký số là mô phỏng. Muốn dùng thật, hãy đối
chiếu với bộ thủ tục hành chính đang áp dụng, hoặc chép thư mục này làm điểm xuất phát (xem
[Tự tạo bản mở rộng](../../README.md#tự-tạo-bản-mở-rộng)).

```
expansion/mot-cua-xa/
├── packs/mot-cua-xa/         gói giao diện “Một cửa cấp xã”
└── plugins/
    ├── so-van-ban/           Sổ văn bản                (plugin kết nối, cổng 9203)
    ├── ky-so/                Ký số văn bản             (plugin kết nối, cổng 9204)
    ├── tiep-nhan/            Tiếp nhận trực tuyến      (plugin kết nối, cổng 9206)
    ├── tinh-han/             Tính hạn theo ngày làm việc (plugin đóng gói)
    └── doc-giay-to/          Đọc giấy tờ, điền sẵn     (plugin đóng gói)
```

Sổ văn bản, Ký số và Tính hạn cũng được bản [Văn thư – điều hành](../van-thu/README.md) dùng chung. Sửa các plugin
này thì nhớ kiểm tra cả bản đó.

## Gói giao diện `vn.mo-rong.mot-cua-xa`

| Phần | Nội dung |
|---|---|
| Giao diện | Màu đỏ – vàng, logo, trang đăng nhập “Bộ phận Một cửa điện tử” với nút “Đăng nhập cán bộ” và ghi chú cho người dân. Đổi “Hồ sơ” thành “Hồ sơ thủ tục”. Ẩn Nhắn tin. |
| Quy trình và biểu mẫu | Đăng ký khai sinh, kết hôn, khai tử; Chứng thực bản sao; Xác nhận tình trạng hôn nhân; Hoà giải ở cơ sở; mẫu “Lấy ý kiến ban, ngành” |
| Luồng tự động (cài ở trạng thái **tắt**) | Nhắc hồ sơ bị trả lại mà 1 ngày chưa bổ sung; Cảnh báo hồ sơ quá hạn; Báo lãnh đạo khi hồ sơ bị từ chối |
| Kiến thức cho trợ lý AI | Hướng dẫn tiếp nhận, thời hạn giải quyết, hồ sơ nộp trực tuyến |

Biểu mẫu có sẵn các trường mà plugin dùng. Đổi mã trường thì phải đổi cả plugin:

| Trường | Plugin dùng |
|---|---|
| `ho_ten`, `ngay_sinh`, `so_cccd`, `noi_thuong_tru` | Đọc giấy tờ |
| `so_van_ban`, `ngay_van_ban` | Sổ văn bản |
| `ma_tra_cuu` | Tiếp nhận trực tuyến |
| `so_ngay_giai_quyet` | Tính hạn |

## Plugin

| Plugin | Dạng | Làm gì | Gắn vào Desktiny |
|---|---|---|---|
| **Sổ văn bản** `so-van-ban` | kết nối | Sổ theo loại văn bản, số liên tục theo năm, không nhảy số, không trùng; số đã huỷ vẫn giữ trong sổ | Bước **Cấp số văn bản**; nút *Cấp số văn bản* trên hồ sơ (ghi số và ngày vào hồ sơ); tab *Số văn bản*; trang *Sổ văn bản* |
| **Ký số văn bản** `ky-so` | kết nối | Ký tài liệu của hồ sơ bằng mã PIN cá nhân, gắn phiếu xác nhận (PDF) có mã; trang công khai để kiểm mã | Bước chạy lâu **Ký số văn bản** (chờ người ký); trang *Văn bản chờ ký*; nút *Ký số* |
| **Tiếp nhận trực tuyến** `tiep-nhan` | kết nối | Trang công khai để nộp yêu cầu và tra cứu tình trạng bằng mã tra cứu và mã bí mật (không cần tài khoản); nhận hồ sơ từ hệ thống ngoài bằng khoá | Sự kiện **có yêu cầu nộp trực tuyến** để luồng tạo hồ sơ; cập nhật tình trạng theo sự kiện của hồ sơ; khung trên hồ sơ |
| **Tính hạn theo ngày làm việc** `tinh-han` | đóng gói | Tính hạn bỏ cuối tuần và ngày lễ, có tính ngày làm bù | Trang *Tính hạn giải quyết*; khung *Hạn giải quyết* trên hồ sơ |
| **Đọc giấy tờ, điền sẵn** `doc-giay-to` | đóng gói | Đọc lớp chữ của tài liệu đã nộp (văn bản, PDF có chữ) hoặc nội dung dán vào; nhận ra họ tên, ngày sinh, số định danh, quê quán, nơi thường trú, MST, điện thoại | Nút *Đọc giấy tờ* trên hồ sơ: cán bộ xem, sửa, xác nhận rồi mới ghi vào hồ sơ |

## Cài đặt

Cài theo [hướng dẫn chung](../../README.md#cài-vào-desktiny), với các điểm riêng sau:

1. Đóng gói cả bản: `build.bat mot-cua-xa` (hoặc `python scripts/dong_goi.py mot-cua-xa`).
2. **Tính hạn** và **Đọc giấy tờ** là plugin đóng gói, không cần máy chủ. Khi duyệt quyền cho Đọc giấy tờ, cấp đủ các
   trường được ghi.
3. Ba plugin kết nối cần máy chủ plugin. Biến trong `deploy/.env`:

   | Plugin | Cổng | Biến |
   |---|---|---|
   | Sổ văn bản | 9203 | `SO_VAN_BAN_TOKEN`, `SO_VAN_BAN_SECRET` |
   | Ký số văn bản | 9204 | `KY_SO_TOKEN`, `KY_SO_SECRET` |
   | Tiếp nhận trực tuyến | 9206 | `TIEP_NHAN_TOKEN`, `TIEP_NHAN_SECRET`; `TIEP_NHAN_TRUST_PROXY=1` chỉ khi đặt sau reverse proxy |

4. **Cấu hình**:
   - **Ký số**: khoá ký của cơ quan (bắt buộc, một chuỗi ngẫu nhiên dài).
   - **Sổ văn bản**: ký hiệu cơ quan.
   - **Tiếp nhận**: tên cơ quan, danh sách thủ tục, khoá cho hệ thống ngoài.
5. **Trang công khai** cần mở ra Internet qua reverse proxy:
   - của Tiếp nhận trực tuyến (cổng 9206): `/cong/nop.html` và `/cong/tra-cuu.html`;
   - trang kiểm mã ký số (cổng 9204): `/cong/xac-thuc.html`.

   Phần còn lại của máy chủ plugin chỉ cần Desktiny gọi tới được.

## Luồng gợi ý

| Mục đích | Bắt đầu | Các bước |
|---|---|---|
| Hồ sơ từ cổng trực tuyến | Sự kiện *Tiếp nhận trực tuyến: Có yêu cầu nộp trực tuyến* | **Tạo hồ sơ** theo biểu mẫu thủ tục, với `ma_tra_cuu` = `{trigger.ma_tra_cuu}`, `ho_ten` = `{trigger.ho_ten}`… |
| Trả kết quả một cửa | Gắn vào quy trình thủ tục | Sau bước lãnh đạo: **Cấp số văn bản** (sổ `GXN`) → **Ký số văn bản** → thông báo `Số {cap_so.so_van_ban}` |

## An toàn riêng của bản này

- Mã PIN ký số được lưu dạng PBKDF2 và bị khoá sau 5 lần nhập sai.
- Trang nộp công khai có câu hỏi kiểm tra và giới hạn 5 lần/giờ cho mỗi địa chỉ. Trang tra cứu không hiện nội dung
  hồ sơ.
- Sổ văn bản: người dùng chỉ thấy số của hồ sơ họ mở được và số họ tự cấp. Cả sổ chỉ xem được ở trang quản trị.

## Cần sửa trước khi dùng thật

- **Ký số đang là mô phỏng** (HMAC bằng khoá của cơ quan) để chạy trọn quy trình. Muốn có giá trị pháp lý, phải thay
  `Signer` trong `plugins/ky-so/server.py` bằng chữ ký từ chứng thư số của tổ chức cung cấp dịch vụ được cấp phép.
- **Ngày lễ** (`plugins/tinh-han/ui/ngay-lam-viec.js`) và thời hạn thủ tục chỉ là mặc định. Sửa theo thông báo nghỉ lễ
  hằng năm và bộ thủ tục đang áp dụng, rồi đóng gói lại.
- **Đọc giấy tờ** chỉ đọc được lớp chữ. Với ảnh quét, cần dùng ứng dụng quét có nhận dạng chữ rồi dán nội dung vào.
  Mọi giá trị đều cần cán bộ kiểm tra trước khi ghi.
- **Kiến thức** trong `packs/mot-cua-xa/knowledge/` là mẫu, cần đối chiếu với văn bản hiện hành.
- Với Desktiny hiện tại, chủ hồ sơ chưa trình được hồ sơ do bước **Tạo hồ sơ** của luồng tạo ra (Core chưa cấp quyền
  bản ghi cho người đó). Luồng “Hồ sơ từ cổng trực tuyến” chỉ chạy trọn vẹn khi Desktiny sửa lỗi này.
