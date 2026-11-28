<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Tự tạo bản mở rộng

Quay lại [README](../README.md).

Không cần làm tất cả. Phần lớn nhu cầu chỉ cần **bước 1–2** (gói giao diện), mà không phải viết dòng mã nào. Chỉ thêm
plugin khi Desktiny chưa có sẵn chức năng bạn cần.

### Bước 1. Tạo thư mục

Đặt tên bằng chữ thường không dấu, nối bằng gạch ngang, ví dụ `ke-toan`:

```
expansion/ke-toan/
├── README.md
├── packs/ke-toan/
└── plugins/
```

Cách nhanh nhất là **chép một bản mẫu** gần với nghiệp vụ của bạn rồi sửa. Tên gói và tên plugin không được trùng giữa
các bản mở rộng. Bước đóng gói tự tìm thư mục mới; không phải khai báo ở đâu cả.

Cần một plugin mà bản mở rộng khác đã có (ví dụ Sổ văn bản, Ký số)? Đừng chép mã. Hãy khai nó trong
`dung-chung.json`:

```json
{ "plugins": ["so-van-ban", "ky-so"] }
```

Khi đóng gói bản của bạn, các plugin này được đóng gói kèm vào `dist/<tên bản>/`, nên thư mục đó vẫn đủ để cài. Bản
Văn thư là ví dụ.

### Bước 2. Gói giao diện

**Cách 1 (khuyên dùng): tạo ngay trong Desktiny rồi xuất ra.**

1. Trong Desktiny, dựng sẵn những gì bản mở rộng cần:
   - biểu mẫu và quy trình (**Quy trình nghiệp vụ**, vẽ trên canvas);
   - luồng tự động;
   - bài kiến thức cho trợ lý AI.
2. **Quản trị › Gói giao diện › Tạo gói của cơ quan**:
   - chọn tên, logo, màu, trang đăng nhập, từ ngữ, menu và trang chủ (có xem trước);
   - tick các quy trình, luồng và bài kiến thức muốn mang theo;
   - **Lưu gói**.
3. Bấm **Xuất** ở dòng gói đó để tải về tệp `.zip`.
4. Giải nén vào `expansion/ke-toan/packs/ke-toan/`. Mở `desktiny-pack.json` và sửa:
   - đổi `id` từ `local.…` sang mã riêng, ví dụ `vn.co-quan.ke-toan` (chữ thường, có ít nhất một dấu chấm);
   - điền `description`, `authors`;
   - đặt `version` (`1.0.0`, tăng lên mỗi lần phát hành).

**Cách 2: viết tay.** `desktiny-pack.json` tối thiểu:

```json
{
  "schema": "desktiny-pack/1",
  "id": "vn.co-quan.ke-toan",
  "name": "Kế toán nội bộ",
  "version": "1.0.0",
  "license": "Apache-2.0",
  "authors": ["Phòng CNTT"],
  "description": "Giao diện và quy trình cho phòng kế toán.",
  "appearance": {
    "app_name": "Kế toán số",
    "org_name": "Công ty ABC",
    "logo": "assets/logo.svg",
    "colors": { "light": { "teal": "#1d4ed8", "teal-strong": "#1e40af", "teal-soft": "#e8eefc" } },
    "login": { "style": "framed", "title": "Phòng Kế toán", "button_label": "Đăng nhập", "note": "Chỉ dành cho nhân viên." },
    "terminology": { "Hồ sơ": "Chứng từ" },
    "menu": { "hide": ["feed"] }
  },
  "processes": ["processes/de-nghi-thanh-toan.json"],
  "automations": [],
  "knowledge": ["knowledge/quy-che-chi-tieu.md"]
}
```

Mỗi tệp mà gói trỏ tới là một phần:

| Thư mục | Nội dung |
|---|---|
| `assets/` | logo, ảnh nền đăng nhập (SVG, PNG) |
| `processes/*.json` | một quy trình kèm biểu mẫu của nó (`name`, `form.fields`, `graph`) |
| `automations/*.json` | một luồng tự động (`name`, `graph`), cài ở trạng thái tắt |
| `knowledge/*.md` | bài kiến thức cho trợ lý AI, viết bằng Markdown |

Tệp quy trình và luồng có cấu trúc dài, nên hãy vẽ trên Desktiny rồi xuất (cách 1) thay vì viết tay. Có thể mở các
tệp trong bản mẫu ra để xem cấu trúc. Đặc tả đầy đủ có trong `docs/packs.md` của Desktiny.

Một số giới hạn Desktiny kiểm tra khi cài:
- màu nền trang đăng nhập phải đủ tối để chữ trắng đọc được (tương phản ≥ 4,5:1);
- chỉ ẩn được các phân hệ Công việc, Hồ sơ, Nhắn tin, Bảng tin, Tài liệu, Báo cáo;
- gói không chứa mã chạy được.

### Bước 3. Plugin đóng gói (khi cần một trang hoặc khung tính toán)

Dùng plugin đóng gói khi chức năng chạy được hoàn toàn trên trình duyệt (tính toán, tra cứu, điền sẵn), không cần lưu
dữ liệu riêng. Ví dụ: `expansion/mot-cua-xa/plugins/tinh-han/`.

```
plugins/tinh-tam-ung/
├── desktiny-plugin.json
└── ui/
    └── tinh-tam-ung.html
```

```json
{
  "schema": "desktiny-plugin/2",
  "id": "vn.co-quan.tinh-tam-ung",
  "name": "Tính tạm ứng",
  "version": "1.0.0",
  "license": "Apache-2.0",
  "authors": ["Phòng CNTT"],
  "description": "Khung trên chứng từ: số tiền tạm ứng còn lại.",
  "permissions": ["cases.read"],
  "ui": [{ "slot": "case.side", "title": "Tạm ứng", "url": "/ui/tinh-tam-ung.html", "height": 180 }]
}
```

Trang gọi Desktiny qua SDK. Bước đóng gói tự chép `desktiny-plugin-sdk.js` và `chung.css` vào cạnh trang:

```html
<link rel="stylesheet" href="chung.css" />
<div id="out" class="muted">Đang tính…</div>
<script type="module">
  import { connect } from './desktiny-plugin-sdk.js'
  const desktiny = connect()
  const context = await desktiny.context                        // hồ sơ / công việc đang mở
  const dossier = await desktiny.api(`/cases/${context.record.case_id}`)
  document.getElementById('out').textContent = `Đề nghị: ${dossier.payload.so_tien ?? 0} đ`
</script>
```

Các chỗ gắn (`slot`):

| Slot | Ở đâu |
|---|---|
| `page` | trang riêng có mục trên thanh bên |
| `admin.page` | trang quản trị của plugin |
| `case.side` | khung trên hồ sơ |
| `case.tab` | tab trên hồ sơ |
| `case.action` | nút thao tác trên hồ sơ |
| `task.side` | khung trên công việc |
| `task.action` | nút thao tác trên công việc |
| `home.widget` | khối trên trang chủ |

Chỉ xin những quyền (`permissions`) thật sự cần. Quản trị viên sẽ thấy và duyệt từng quyền.

### Bước 4. Plugin kết nối (khi cần lưu dữ liệu, chạy nền, nhận sự kiện)

Dùng plugin kết nối khi chức năng cần một trong các việc sau:
- lưu dữ liệu riêng;
- chạy theo lịch;
- nhận sự kiện của Desktiny;
- làm một bước trong quy trình;
- trả lời trợ lý AI;
- có trang công khai cho người ngoài.

Ví dụ gọn: `expansion/nhan-su/plugins/nhac-han/`, `expansion/van-thu/plugins/so-van-ban-den/`.

```
plugins/so-quy/
├── desktiny-plugin.json     có "base_url" — đó là dấu hiệu plugin kết nối
├── server.py
└── ui/so-quy.html
```

`server.py` dùng bộ khung `lib/mo_rong`. Bộ khung đã lo kiểm chữ ký, xác định người đang xem, lưu SQLite và trả lỗi
dạng JSON:

```python
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "lib"))

from mo_rong import App, Response, Settings, Store  # noqa: E402

SCHEMA = "CREATE TABLE IF NOT EXISTS phieu (id INTEGER PRIMARY KEY, noi_dung TEXT NOT NULL, so_tien INTEGER NOT NULL);"


def build(settings: Settings | None = None, store: Store | None = None) -> App:
    app = App("so-quy", HERE, settings)
    db = store or Store(app.settings.data_dir / "so-quy.sqlite3", SCHEMA)

    @app.route("GET", "/api/phieu", viewer=True)        # gọi từ trang plugin, bằng phiên người đang xem
    def danh_sach(request):
        return {"items": db.all("SELECT * FROM phieu ORDER BY id DESC")}

    @app.route("POST", "/events", signed=True)          # Desktiny gọi tới, có chữ ký HMAC
    def su_kien(request):
        return Response(202, b"{}")

    return app


if __name__ == "__main__":
    build().run(9210)
```

Trang gọi máy chủ của chính plugin bằng `sdk/mo-rong.js`: `import { server } from './mo-rong.js'`, rồi
`await server('api/phieu')`.

Để chạy cùng các plugin khác, cần thêm:
- một dịch vụ trong `deploy/compose.yaml` (chép dịch vụ có sẵn, đổi `PLUGIN`, `PORT`, tên biến, volume);
- cặp biến `<TÊN>_TOKEN`, `<TÊN>_SECRET` trong `deploy/.env.example`.

Cổng trong `base_url`, `server.py` và `compose.yaml` phải trùng nhau. Bản mẫu đang dùng 9201–9209, nên plugin mới bắt
đầu từ 9210.

Manifest của plugin kết nối có thể khai thêm:
- `events` (nhận sự kiện của Desktiny), `emits` (phát sự kiện riêng);
- `nodes` (bước quy trình, kể cả bước chạy lâu);
- `assistant_tools` (công cụ cho trợ lý AI);
- `settings_schema` (cấu hình theo cơ quan);
- `health_endpoint`.

Đặc tả có trong `docs/plugins.md` của Desktiny; các plugin kết nối trong bản mẫu dùng đủ các loại này.

Lưu ý khi ghi vào biểu mẫu (quyền `cases.fields.write`): Desktiny chỉ cho plugin ghi trường **trong phiên của một
người dùng**, tức từ nút hay khung mà người đó đang mở. Trong bước quy trình, plugin chạy bằng token cài đặt nên không
ghi được. Hãy trả giá trị ra làm đầu ra của bước, rồi để quy trình ghi bằng bước **Cập nhật hồ sơ** có sẵn (ví dụ
`form.so_den` = `{vao_so.so_den}`).

### Bước 5. Đóng gói, thử, viết README

1. `build.bat ke-toan`. Bước đóng gói kiểm mọi manifest theo đúng quy tắc của Desktiny; có lỗi thì báo tệp nào, cần
   sửa gì.
2. Cài thử vào một Desktiny thử nghiệm theo mục [Cài vào Desktiny](../README.md#cài-vào-desktiny).
3. Viết test cho máy chủ plugin trong `tests/`. `tests/conftest.py` có sẵn một Desktiny giả để gọi thử sự kiện, bước
   và trang. Chạy `make test`.
4. Viết `expansion/ke-toan/README.md`: dành cho ai, có gì, cài và cấu hình thế nào, cần sửa gì trước khi dùng thật.
   Có thể theo mẫu README của hai bản mẫu.

### Danh sách kiểm tra trước khi phát hành

- [ ] `id` riêng, không bắt đầu bằng `local.`; `version` đã tăng so với bản trước.
- [ ] Gói không chứa tên, số liệu hay tài liệu nội bộ không được phép chia sẻ.
- [ ] Plugin chỉ xin quyền cần dùng; trang không gửi dữ liệu ra ngoài máy chủ của plugin.
- [ ] Mã trường biểu mẫu mà plugin đọc/ghi khớp với biểu mẫu trong gói.
- [ ] `make test` và `make lint` qua; đã cài thử trên Desktiny thật.
- [ ] README của bản mở rộng đã ghi rõ những gì chỉ là mẫu.
