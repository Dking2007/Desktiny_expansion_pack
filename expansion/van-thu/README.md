<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Bản mẫu: Văn thư – điều hành

Bản mở rộng mẫu cho **công tác văn thư và điều hành** của cơ quan:
- **Văn bản đến:** vào sổ, lãnh đạo cho ý kiến chỉ đạo, giao người xử lý, theo dõi hạn.
- **Văn bản đi:** dự thảo, kiểm tra nội dung và thể thức, ký ban hành, cấp số, ký số.
- **Lập hồ sơ:** nộp lưu hồ sơ vào lưu trữ cơ quan.

Đây là **bản mẫu**: tên cơ quan là tên giả, quy trình và hướng dẫn chỉ là tóm tắt để tham khảo. Trước khi dùng thật,
hãy đối chiếu với quy định hiện hành về công tác văn thư và quy chế làm việc của cơ quan (xem
[Cần sửa trước khi dùng thật](#cần-sửa-trước-khi-dùng-thật)).

```
expansion/van-thu/
├── packs/van-thu/            gói giao diện “Văn thư – điều hành”
├── plugins/
│   └── so-van-ban-den/       Sổ văn bản đến     (plugin kết nối, cổng 9207)
└── dung-chung.json           dùng chung với bản Một cửa: Sổ văn bản, Ký số, Tính hạn
```

Bản này **dùng chung** ba plugin của bản [Một cửa cấp xã](../mot-cua-xa/README.md) thay vì sao chép chúng:
- **Sổ văn bản**: cấp số văn bản đi;
- **Ký số**: ký văn bản;
- **Tính hạn**: tính hạn theo ngày làm việc.

Khi đóng gói bản Văn thư, ba plugin này được đóng gói kèm vào `dist/van-thu/`. Cơ quan đã cài chúng từ bản Một cửa
thì không cần cài lại.

## Gói giao diện `vn.mo-rong.van-thu`

| Phần | Nội dung |
|---|---|
| Giao diện | Tên “Văn phòng điện tử”, màu chàm (sáng và tối), logo, trang đăng nhập “Văn bản đến · Văn bản đi · Hồ sơ lưu trữ”. Đổi “Hồ sơ” thành “Văn bản”, “Cần phê duyệt” thành “Chờ cho ý kiến”. Ẩn Bảng tin. Trang chủ ưu tiên khối của plugin. |
| Quy trình và biểu mẫu | **Xử lý văn bản đến** (lãnh đạo chỉ đạo, giao xử lý → người được giao xử lý, báo cáo kết quả); **Ban hành văn bản đi** (lãnh đạo đơn vị kiểm tra nội dung và thể thức → lãnh đạo cơ quan ký); **Nộp lưu hồ sơ vào lưu trữ cơ quan** (lãnh đạo đơn vị duyệt) |
| Luồng tự động (cài ở trạng thái **tắt**) | Cảnh báo văn bản quá hạn xử lý; Báo văn bản bị trả lại; Báo công việc quá hạn |
| Kiến thức cho trợ lý AI | Xử lý văn bản đến; Ban hành văn bản đi; Thể thức văn bản hành chính (tóm tắt); Lập hồ sơ và nộp lưu |

Quy trình “Xử lý văn bản đến” chọn người xử lý theo trường **Người xử lý chính**:
- lãnh đạo ghi **họ tên đầy đủ** đúng như tên tài khoản trong Desktiny;
- tên không khớp, hoặc trùng với hai người, thì bước xử lý không tìm được người nhận.

Biểu mẫu có sẵn các trường mà plugin dùng. Đổi mã trường thì phải đổi cả plugin:

| Biểu mẫu | Trường | Plugin dùng |
|---|---|---|
| Phiếu vào sổ văn bản đến | `noi_gui`, `so_ky_hieu_goc`, `ngay_van_ban`, `loai_van_ban`, `trich_yeu`, `do_khan`, `han_xu_ly` (đọc); `so_den`, `ngay_den` (ghi) | Sổ văn bản đến |
| Phiếu trình ban hành văn bản | `so_van_ban`, `ngay_van_ban` (ghi) | Sổ văn bản |

## Plugin

| Plugin | Dạng | Làm gì | Gắn vào Desktiny |
|---|---|---|---|
| **Sổ văn bản đến** `so-van-ban-den` | kết nối, 9207 | Vào sổ văn bản đến: số đến liên tục theo năm, không nhảy số, không trùng; mỗi văn bản một số. Ghi số đến, ngày đến vào văn bản. Theo dõi văn bản đang xử lý, sắp đến hạn, quá hạn; đóng khi văn bản kết thúc. Số vào nhầm thì huỷ (giữ trong sổ, ghi lý do). | Nút *Vào sổ văn bản đến* và khung *Sổ văn bản đến* trên văn bản; trang *Sổ văn bản đến* (lọc, tìm, xuất CSV); khối trang chủ *Văn bản đến cần xử lý*; bước quy trình **Vào sổ văn bản đến**; trợ lý AI trả lời “có văn bản đến nào quá hạn không”; trang quản trị |
| Sổ văn bản `so-van-ban` | kết nối, 9203 | dùng chung với bản Một cửa | Cấp số văn bản đi theo sổ (Quyết định, Công văn, Thông báo…) |
| Ký số văn bản `ky-so` | kết nối, 9204 | dùng chung với bản Một cửa | Ký văn bản đã duyệt |
| Tính hạn `tinh-han` | đóng gói | dùng chung với bản Một cửa | Tính hạn xử lý theo ngày làm việc |

Người dùng chỉ thấy trong sổ những văn bản họ mở được và những văn bản họ tự vào sổ. Cả sổ chỉ xem được ở trang quản
trị.

### Giao diện Sổ văn bản đến

Các trang dùng bộ giao diện chung `sdk/giao-dien.css` và `sdk/bieu-do.js`, có phông chữ của Desktiny đi kèm. Điểm nhấn là
**dấu “ĐẾN”** vẽ theo mẫu Nghị định 30 (Số, Ngày, Chuyển, Lưu hồ sơ số) bằng mực đỏ, chữ điền màu mực xanh; đây là hình
vẽ chỉ trạng thái, không mô phỏng con dấu thật.

| Trang | Thấy và làm được gì |
|---|---|
| *Sổ văn bản đến* | Chọn năm; bốn số liệu đồng thời là bộ lọc (đã vào sổ, đang xử lý, quá hạn, đã xử lý); sổ đăng ký kẻ dòng theo cột của sổ giấy, dải 12 tháng, tìm ngay khi gõ, hạn xử lý bằng tờ lịch nhỏ, đỏ khi quá hạn; mở hồ sơ; xuất bảng để sao chép |
| *Vào sổ văn bản đến* | Thông tin văn bản bên trái, bản xem trước văn bản đến kèm dấu “ĐẾN” với số sẽ cấp bên phải; hỏi lại rồi đóng dấu, số đến hiện lớn |
| Khung *Sổ văn bản đến* trên hồ sơ | Dấu “ĐẾN” đã điền, trạng thái, độ khẩn và hạn xử lý đếm ngược |
| Khối *Văn bản đến cần xử lý* | Số văn bản đang mở, lọc quá hạn / sắp đến hạn / còn hạn, năm văn bản gấp nhất, bấm để mở |
| Quản trị *Sổ văn bản đến* | Dấu xem trước cho số tiếp theo, cách sổ hoạt động bằng lời, thước ngày cho mốc “sắp đến hạn”, biểu đồ theo tháng, huỷ số có lý do |

## Cài đặt

Cài theo [hướng dẫn chung](../../README.md#cài-vào-desktiny), với các điểm riêng sau:

1. Đóng gói cả bản: `build.bat van-thu` (hoặc `python scripts/dong_goi.py van-thu`). Thư mục `dist/van-thu/` có gói
   giao diện, Sổ văn bản đến và ba plugin dùng chung.
2. Plugin kết nối và biến trong `deploy/.env`:

   | Plugin | Cổng | Biến |
   |---|---|---|
   | Sổ văn bản đến | 9207 | `SO_VAN_BAN_DEN_TOKEN`, `SO_VAN_BAN_DEN_SECRET` |
   | Sổ văn bản | 9203 | `SO_VAN_BAN_TOKEN`, `SO_VAN_BAN_SECRET` |
   | Ký số văn bản | 9204 | `KY_SO_TOKEN`, `KY_SO_SECRET` |

3. **Cấu hình**:
   - **Sổ văn bản**: ký hiệu cơ quan (ví dụ `UBND`).
   - **Ký số**: khoá ký của cơ quan.
   - **Sổ văn bản đến**: báo “sắp đến hạn” trước mấy ngày (mặc định 2).
4. Cấp vai trò trong Desktiny cho đúng người:
   - **Ban giám đốc** (`director`): lãnh đạo cơ quan, người cho ý kiến chỉ đạo và ký;
   - **trưởng đơn vị** (lãnh đạo phòng trong Cơ cấu tổ chức): người kiểm tra văn bản đi và duyệt nộp lưu của phòng.
5. **Thêm bước của Văn phòng** (nên làm). Gói không biết trước phòng nào là Văn phòng của cơ quan, nên quy trình mẫu
   chưa có bước văn phòng kiểm tra thể thức hay tiếp nhận nộp lưu. Sau khi cài, mở quy trình ở **Quy trình nghiệp vụ**,
   chèn một bước duyệt với người duyệt **Đơn vị → Văn phòng**:
   - “Ban hành văn bản đi”: chèn trước bước lãnh đạo ký;
   - “Nộp lưu hồ sơ”: chèn sau bước lãnh đạo đơn vị.

## Cách dùng hằng ngày

**Văn bản đến**
1. Văn thư tạo văn bản theo quy trình “Xử lý văn bản đến”, đính kèm bản quét, rồi bấm **Vào sổ văn bản đến** để lấy
   số đến.
2. Trình văn bản. Lãnh đạo ghi ý kiến chỉ đạo, người xử lý chính và hạn.
3. Người được giao xử lý, ghi kết quả, chọn Duyệt. Văn bản kết thúc và sổ ghi “Đã xử lý”.

**Văn bản đi**
1. Chuyên viên trình dự thảo theo quy trình “Ban hành văn bản đi”.
2. Sau khi lãnh đạo ký, văn thư bấm **Cấp số văn bản** (Sổ văn bản) và **Ký số**.

## Luồng gợi ý

Dựng trên trình thiết kế quy trình của Desktiny sau khi cài plugin:

| Mục đích | Bắt đầu | Các bước |
|---|---|---|
| Tự vào sổ khi trình | Trong quy trình “Xử lý văn bản đến”, ngay sau bước bắt đầu | **Vào sổ văn bản đến** → **Cập nhật hồ sơ**: `form.so_den` = `{vao_so.so_den}`, `form.ngay_den` = `{vao_so.ngay_den}` |
| Cấp số, ký số tự động | Quy trình “Ban hành văn bản đi”, sau bước lãnh đạo ký | **Cấp số văn bản** (sổ theo loại) → **Ký số văn bản** → thông báo `Đã ban hành văn bản số {cap_so.so_van_ban}` |
| Nhắc văn bản khẩn | Sự kiện *Hồ sơ được trình* | **Điều kiện** `form.do_khan` khác “Thường” → **Thông báo** lãnh đạo ngay |

Bước plugin không tự ghi vào biểu mẫu được: Desktiny chỉ cho plugin ghi trường trong phiên của một người dùng. Vì thế
luồng tự vào sổ dùng thêm bước **Cập nhật hồ sơ** có sẵn của Desktiny. Nút trên văn bản thì ghi được ngay, vì nó chạy
bằng phiên của người bấm.

## Cần sửa trước khi dùng thật

- **Quy định:** các bài kiến thức trong `packs/van-thu/knowledge/` là tóm tắt. Đối chiếu với văn bản hiện hành về công
  tác văn thư, thể thức văn bản, thời hạn bảo quản tài liệu và quy chế của cơ quan, rồi sửa cho đúng.
- **Văn bản mật:** không xử lý trên hệ thống này. Trang đăng nhập đã ghi chú điều đó.
- **Ký số đang là mô phỏng** (xem bản Một cửa). Văn bản điện tử có giá trị pháp lý cần chữ ký số từ chứng thư số hợp
  lệ.
- **Danh mục hồ sơ, thời hạn bảo quản:** các lựa chọn trong biểu mẫu nộp lưu chỉ là mẫu. Thay bằng danh mục hồ sơ và
  bảng thời hạn bảo quản của cơ quan.
- **Người xử lý** được chọn theo họ tên. Đơn vị có hai người trùng họ tên thì nên đổi bước “Xử lý và báo cáo kết quả”
  sang chọn người cụ thể hoặc theo phòng.
