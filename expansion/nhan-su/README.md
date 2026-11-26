<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Bản mẫu: Nhân sự doanh nghiệp

Bản mở rộng mẫu biến Desktiny thành **cổng nhân sự nội bộ** cho doanh nghiệp hoặc cơ quan nhỏ. Người lao động chấm
công, gửi đơn từ và xem phiếu lương. Bộ phận nhân sự tính lương, chấm KPI và được nhắc trước khi hợp đồng hết hạn.

Đây là **bản mẫu**: dùng thử ngay được, nhưng tên công ty là tên giả. Quy chế, mức lương và biểu thuế chỉ để minh hoạ.
Muốn dùng thật, hãy sửa theo quy định của đơn vị, hoặc chép thư mục này làm điểm xuất phát cho bản của riêng bạn
(xem [Tự tạo bản mở rộng](../../README.md#tự-tạo-bản-mở-rộng)).

```
expansion/nhan-su/
├── packs/nhan-su/            gói giao diện “Nhân sự doanh nghiệp”
└── plugins/
    ├── cham-cong/            Chấm công GPS         (plugin kết nối, cổng 9201)
    ├── luong-kpi/            Tiền lương và KPI     (plugin kết nối, cổng 9202)
    └── nhac-han/             Nhắc hạn hồ sơ        (plugin kết nối, cổng 9205)
```

## Gói giao diện `vn.mo-rong.nhan-su`

| Phần | Nội dung |
|---|---|
| Giao diện | Tên “Nhân sự số”, màu xanh ngọc (sáng và tối), logo, trang đăng nhập riêng “Cổng nhân sự nội bộ”. Đổi “Hồ sơ” thành “Đơn từ”, “Phòng ban” thành “Bộ phận”. Ẩn Bảng tin. Trang chủ ưu tiên khối của plugin. |
| Quy trình và biểu mẫu | Đơn nghỉ phép (trên 3 ngày thì lên Giám đốc), Điều chỉnh công, Làm thêm giờ (trên 4 giờ thì lên Giám đốc), Đổi ca, Phê duyệt bảng lương tháng, Đánh giá KPI, Gia hạn hợp đồng/giấy tờ |
| Luồng tự động (cài ở trạng thái **tắt**) | Nhắc đơn bị trả lại mà 1 ngày chưa bổ sung; Cảnh báo đơn quá hạn; Báo công việc quá hạn |
| Kiến thức cho trợ lý AI | Quy chế chấm công, quy chế nghỉ phép, cách tính lương, đánh giá KPI |

Các luồng tự động chỉ dùng sự kiện có sẵn của Desktiny, nên chạy được cả khi chưa cài plugin. Bật chúng ở **Quy trình
nghiệp vụ** sau khi xem lại người nhận.

Biểu mẫu có sẵn các trường mà plugin dùng. Đổi mã trường thì phải đổi cả cấu hình plugin:

| Trường | Plugin dùng |
|---|---|
| `diem_kpi`, `xep_loai` | Tiền lương và KPI |
| `ngay_het_han` | Nhắc hạn hồ sơ |

## Plugin

| Plugin | Làm gì | Gắn vào Desktiny |
|---|---|---|
| **Chấm công GPS** `cham-cong` | Vào/ra ca bằng vị trí GPS trong bán kính trụ sở; ca làm, giờ cho phép đến muộn; tổng hợp công tháng, xuất CSV | Trang *Chấm công*; khối trang chủ; trang quản trị *Ca làm và địa điểm*; sự kiện **đi muộn quá N lần/tháng**; trợ lý trả lời được “tháng này tôi đi muộn mấy lần” |
| **Tiền lương và KPI** `luong-kpi` | Bậc lương, hồ sơ lương, tính lương tháng (ngày công lấy từ Chấm công, bảo hiểm, thuế TNCN luỹ tiến), chốt kỳ, phiếu lương; chấm KPI theo tiêu chí có trọng số | Bước quy trình chạy lâu **Chốt kỳ lương**; trang *Phiếu lương*; tab *Chấm điểm KPI* trong hồ sơ (ghi điểm và xếp loại vào hồ sơ); trợ lý đọc phiếu lương |
| **Nhắc hạn hồ sơ** `nhac-han` | Theo dõi trường ngày hết hạn (hợp đồng, giấy phép…) trong hồ sơ của các quy trình được chọn; nhắc trước 30, 7, 1 ngày và đúng ngày | Sự kiện **sắp hết hạn**; khối trang chủ; trang quản trị; trợ lý liệt kê hồ sơ sắp hết hạn |

### Giao diện các trang

Các trang dựng trên bộ giao diện dùng chung `sdk/giao-dien.css` và `sdk/bieu-do.js` (biểu đồ vẽ bằng SVG, không tải gì
từ bên ngoài), theo màu sáng/tối của Desktiny:

| Trang | Thấy và làm được gì |
|---|---|
| *Chấm công* | Đồng hồ và lời chào; một nút lớn đổi theo trạng thái (Vào ca → Ra ca → Đã xong), báo từng bước lấy GPS; ca hôm nay vẽ trên trục giờ (ca, thời gian đã làm, lượt chấm, “bây giờ”); ô số liệu tháng, vòng tỉ lệ đúng giờ; lịch tháng tô màu đúng giờ, muộn, về sớm, vắng, bấm một ngày để xem chi tiết; hỏi lại trước khi ra ca sớm |
| Khối *Chấm công hôm nay* | Trạng thái, giờ vào/ra, thanh tiến độ ca, số liệu tháng, nút mở trang |
| Quản trị *Chấm công* | Danh sách cần làm khi chưa thiết lập; ai có mặt, ai muộn hôm nay; biểu đồ từng ngày trong tháng; bảng từng người kèm dải ô theo ngày, sắp xếp được; ca làm vẽ trên trục 24 giờ; địa điểm dạng thẻ có bán kính, lấy toạ độ từ vị trí hiện tại; xếp ca |
| *Phiếu lương* | Thực lĩnh nổi bật, so với tháng trước, đường xu hướng 12 tháng; thanh “tổng thu nhập đi đâu” (thực lĩnh, bảo hiểm, thuế); giải thích từng dòng; vòng ngày công; bậc thuế đã chạm tới; danh sách các tháng đã chốt |
| Tab *Chấm điểm KPI* | Thanh trượt cho từng tiêu chí kèm trọng số và phần đóng góp; vòng tổng điểm và xếp loại cập nhật ngay khi kéo; thang xếp loại; ghi điểm vào hồ sơ có hỏi lại |
| Quản trị *Tiền lương và KPI* | Các bước tính → chốt → phiếu hiện; số liệu kỳ, xu hướng 12 kỳ, bảng từng người có thanh thực lĩnh; bậc lương dạng bậc thang; hồ sơ lương chọn nhiều người; tiêu chí KPI với thanh trọng số phải đủ 100% |
| Khối *Hồ sơ sắp hết hạn* | Ba ô quá hạn / 7 ngày / 30 ngày (bấm để lọc), dòng thời gian các hồ sơ gần nhất với đếm ngược, bấm để mở hồ sơ |
| Quản trị *Nhắc hạn* | Số liệu theo mức gấp; dải 90 ngày tới theo tuần (bấm để lọc) có vạch mốc nhắc; danh sách theo tháng, tìm không dấu, mỗi hồ sơ có các mốc đã nhắc/sắp nhắc; “Quét ngay” có trạng thái rõ ràng |

## Cài đặt

Cài theo [hướng dẫn chung](../../README.md#cài-vào-desktiny), với các điểm riêng sau:

1. Đóng gói cả bản: `build.bat nhan-su` (hoặc `python scripts/dong_goi.py nhan-su`). Các tệp nằm trong
   `dist/nhan-su/` và `dist/may-chu-plugin/`.
2. Ba plugin đều là plugin kết nối, nên cần chạy máy chủ plugin. Biến trong `deploy/.env`:

   | Plugin | Cổng | Biến |
   |---|---|---|
   | Chấm công GPS | 9201 | `CHAM_CONG_TOKEN`, `CHAM_CONG_SECRET` |
   | Tiền lương và KPI | 9202 | `LUONG_KPI_TOKEN`, `LUONG_KPI_SECRET` |
   | Nhắc hạn hồ sơ | 9205 | `NHAC_HAN_TOKEN`, `NHAC_HAN_SECRET` |

3. Khi duyệt quyền cho **Nhắc hạn**, chọn các quy trình được theo dõi (ví dụ “Gia hạn hợp đồng, giấy tờ”).
4. **Cấu hình** (nút trên dòng plugin ở trang Plugin):
   - **Chấm công**: số lần đi muộn thì báo, sai số GPS tối đa, khoá chia sẻ công (đặt giống bên Tiền lương và KPI).
   - **Tiền lương và KPI**: lương cơ sở, tỉ lệ bảo hiểm, giảm trừ gia cảnh, biểu thuế, địa chỉ plugin Chấm công và khoá
     chia sẻ.
   - **Nhắc hạn**: mã trường ngày hết hạn, các mốc nhắc, chu kỳ quét.

## Luồng gợi ý

Dựng trên trình thiết kế quy trình của Desktiny sau khi cài:

| Mục đích | Bắt đầu | Các bước |
|---|---|---|
| Bảng lương tháng | Quy trình “Phê duyệt bảng lương tháng” | Thêm **Chốt kỳ lương** (`ky` = `{form.ky_luong}`) trước bước trưởng bộ phận |
| Gia hạn hợp đồng | Sự kiện *Nhắc hạn hồ sơ: Hồ sơ sắp hết hạn* | **Giao việc** cho bộ phận nhân sự: “Chuẩn bị gia hạn” |
| Kỷ luật lao động | Sự kiện *Chấm công GPS: Đi muộn quá số lần cho phép* | **Thông báo** cho quản lý trực tiếp |

## Cần sửa trước khi dùng thật

- **Lương**: mức lương cơ sở, tỉ lệ bảo hiểm, giảm trừ gia cảnh và biểu thuế mặc định chỉ để thử. Bộ phận nhân sự đặt
  lại theo quy định hiện hành ở **Cấu hình**.
- **Quy chế** trong `packs/nhan-su/knowledge/` là văn bản mẫu. Thay bằng quy chế của đơn vị để trợ lý AI trả lời đúng.
- **Tên, logo, màu** trong `packs/nhan-su/desktiny-pack.json` và `packs/nhan-su/assets/`.
- Khung plugin không có hộp thoại `alert/prompt` và không tải tệp về được (giới hạn sandbox của Desktiny), nên bảng công
  dạng CSV hiện trong một ô để sao chép.
