<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
-->

# Desktiny Expansion Pack

Bộ mở rộng cho [Desktiny](https://github.com/Dking2007/DXOS_Desktiny) (sản phẩm chính). Repo này:
https://github.com/Dking2007/Desktiny_expansion_pack.

| Expansion Pack | Desktiny tối thiểu | Đã chạy thử |
|---|---|---|
| 1.1.0 | 3.1.0 | 28/11/2026: `tests/desktiny` (cài mọi gói và plugin rồi chạy luồng) đạt 5/5 với mã nguồn tag `v3.1.0`; 27/11/2026: cài thật 3 gói + 9 plugin vào Desktiny `main` (`c4ccb9f`), kiểm sức khỏe 7 máy chủ plugin đạt |

**Các bản mở rộng của Desktiny.** Một bản mở rộng đưa Desktiny vào một nghiệp vụ cụ thể (nhân sự, một cửa, kế toán,
trường học…) mà **không sửa mã của Desktiny**. Nó gồm một **gói giao diện** (màu sắc, từ ngữ, quy trình, biểu mẫu,
kiến thức cho trợ lý AI) và các **plugin** thêm chức năng mới. Tất cả được cài qua trang quản trị của Desktiny bằng
tệp `.zip`.

Repo này có:

- **Ba bản mẫu** dùng thử được ngay, để xem một bản mở rộng hoàn chỉnh trông thế nào.
- **Công cụ đóng gói**: bấm đúp `build.bat` là có các tệp `.zip` để cài.
- **Bộ khung** để tự viết plugin: máy chủ plugin dựng sẵn, SDK cho trang, cấu hình Docker và test.
- **Hướng dẫn tự tạo** bản mở rộng cho nghiệp vụ của bạn (mục [Tự tạo bản mở rộng](#tự-tạo-bản-mở-rộng)).

## Mục lục

1. [Bản mở rộng gồm những gì](#bản-mở-rộng-gồm-những-gì)
2. [Các bản mẫu](#các-bản-mẫu)
3. [Đóng gói](#đóng-gói)
4. [Cài vào Desktiny](#cài-vào-desktiny)
5. [Tự tạo bản mở rộng](#tự-tạo-bản-mở-rộng)
6. [An toàn](#an-toàn)
7. [Giới hạn](#giới-hạn)
8. [Phát triển và kiểm thử](#phát-triển-và-kiểm-thử)
9. [Đóng góp](#đóng-góp)

## Bản mở rộng gồm những gì

Mỗi bản mở rộng là một thư mục trong `expansion/`:

```
expansion/<tên bản mở rộng>/
├── README.md                giới thiệu bản mở rộng
├── packs/<tên gói>/         gói giao diện (thường một gói)
├── plugins/<tên plugin>/    các plugin (không bắt buộc)
└── dung-chung.json          plugin mượn của bản mở rộng khác (không bắt buộc)
```

Bên trong có ba loại thành phần:

| Thành phần | Là gì | Cần biết lập trình? | Cần máy chủ riêng? |
|---|---|---|---|
| **Gói giao diện** (`desktiny-pack/1`) | Dữ liệu thuần: tên, logo, màu, trang đăng nhập, từ ngữ, menu, trang chủ, quy trình và biểu mẫu, luồng tự động, kiến thức cho trợ lý AI | Không: tạo được ngay trong Desktiny rồi xuất ra | Không |
| **Plugin đóng gói** (`desktiny-plugin/2`) | Trang web (HTML, JS) chạy trong khung cách ly của Desktiny, tính toán ngay trên trình duyệt | HTML và JavaScript | Không |
| **Plugin kết nối** (`desktiny-plugin/1`) | Trang web cùng một máy chủ riêng (Python, SQLite). Desktiny gọi máy chủ khi có sự kiện, bước quy trình hay câu hỏi của trợ lý AI | Python | Có, chạy bằng Docker Compose |

```
                 ┌──────────── Desktiny ────────────┐
 người dùng ───▶ │ giao diện (gói)  khung plugin ◀──┼── trang plugin (ui/)
                 │ quy trình, sự kiện, trợ lý AI ───┼──▶ máy chủ plugin kết nối
                 └──────────────────────────────────┘          ▲
 người ngoài ─────────────── trang công khai (nếu plugin có) ──┘
```

Một plugin gắn vào Desktiny ở nhiều chỗ:
- trang riêng trên thanh bên;
- khung hoặc tab trên hồ sơ, công việc;
- nút thao tác;
- khối trên trang chủ;
- bước trong quy trình;
- sự kiện để luồng tự động bắt đầu;
- công cụ cho trợ lý AI.

Plugin chỉ làm được những gì quản trị viên đã duyệt khi cài.

**Yêu cầu:**
- Desktiny **3.1.0** trở lên. Bản 3.0.0 chưa cài được plugin `.zip` và bỏ qua các tuỳ biến đăng nhập mới.
- **Python 3.11+** để đóng gói.
- **Docker** cho máy chủ plugin kết nối.

## Các bản mẫu

| Bản mẫu | Dành cho | Gói giao diện | Plugin |
|---|---|---|---|
| [**Nhân sự doanh nghiệp**](expansion/nhan-su/README.md) `nhan-su` | Bộ phận nhân sự của doanh nghiệp, cơ quan nhỏ | Nhân sự doanh nghiệp: 7 quy trình đơn từ, 3 luồng tự động, quy chế cho trợ lý AI | Chấm công GPS, Tiền lương và KPI, Nhắc hạn hồ sơ |
| [**Một cửa cấp xã**](expansion/mot-cua-xa/README.md) `mot-cua-xa` | Bộ phận một cửa của UBND cấp xã | Một cửa cấp xã: 6 thủ tục hộ tịch, chứng thực, hoà giải; 3 luồng tự động | Sổ văn bản, Ký số, Tiếp nhận trực tuyến, Tính hạn, Đọc giấy tờ |
| [**Văn thư – điều hành**](expansion/van-thu/README.md) `van-thu` | Văn thư, văn phòng của cơ quan | Văn thư – điều hành: xử lý văn bản đến, ban hành văn bản đi, nộp lưu hồ sơ; 3 luồng tự động; hướng dẫn văn thư cho trợ lý AI | Sổ văn bản đến; dùng chung Sổ văn bản, Ký số, Tính hạn của bản Một cửa |

Mỗi bản mẫu có README riêng: nội dung, cách cài, cấu hình, luồng gợi ý và những gì cần sửa trước khi dùng thật. Tên
cơ quan trong bản mẫu là tên giả; quy chế, thời hạn và mức tiền chỉ để minh hoạ.

## Đóng gói

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
    └── may-chu-plugin-1.1.0.zip            mã máy chủ 6 plugin kết nối + Dockerfile + compose.yaml
```

Đóng gói tất cả thì gói máy chủ chứa mọi plugin kết nối; chọn riêng một bản mở rộng thì chỉ chứa plugin của bản đó.

Tên tệp có phiên bản lấy từ manifest (`version`). Cùng mã nguồn luôn cho ra cùng tệp .zip.

## Cài vào Desktiny

Mở `dist/HUONG-DAN-CAI.txt`: tệp này ghi đúng những tệp vừa đóng gói và thứ tự cài. Thứ tự chung như sau.

### 1. Gói giao diện

**Quản trị › Gói giao diện › Tải gói lên (.zip)** → chọn `goi-*.zip` → xem trước → cài → **Dùng giao diện này**.
Cài gói cần quyền quản lý biểu mẫu và trợ lý AI. Cài nhiều gói được, nhưng chỉ một gói là giao diện đang dùng. Luồng tự
động trong gói được cài ở trạng thái tắt: xem lại người nhận rồi bật ở **Quy trình nghiệp vụ**.

### 2. Plugin đóng gói

**Quản trị › Plugin › Cài plugin** → chọn `plugin-*.zip` → **Duyệt quyền**. Không cần máy chủ.

### 3. Máy chủ plugin kết nối

1. Chép `dist/may-chu-plugin/may-chu-plugin-*.zip` lên máy chủ rồi giải nén.
2. `cp deploy/.env.example deploy/.env`, đặt `DESKTINY_URL` (địa chỉ để máy chủ plugin gọi tới Desktiny).
3. `docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build` (trong mã nguồn: `make up`). Một image
   dùng chung cho mọi plugin; dữ liệu SQLite nằm trong volume riêng của từng plugin.
4. Trong cấu hình Desktiny: thêm máy chủ plugin vào `PLUGIN_ALLOWED_HOSTS` (ví dụ `plugins.co-quan.vn`) và thêm
   origin vào `PLUGIN_FRAME_SOURCES` (ví dụ `https://plugins.co-quan.vn`).

Cổng và biến của từng plugin có trong README của bản mẫu. Nếu `--host` là tên miền, reverse proxy cần chuyển
`https://<host>/<tên-plugin>/…` tới cổng tương ứng.

### 4. Plugin kết nối

1. **Quản trị › Plugin › Cài plugin** → chọn `plugin-<tên>-*.zip` → **Duyệt quyền**.
2. Desktiny hiện **token** và **khoá ký** đúng một lần. Chép chúng vào `deploy/.env` (`<TÊN>_TOKEN`, `<TÊN>_SECRET`)
   rồi chạy lại `docker compose … up -d`.

### 5. Cấu hình

Ở trang **Plugin**, mỗi plugin có nút **Cấu hình** (cài đặt theo cơ quan; ô bí mật được mã hoá). Plugin có trang
quản trị thì mở từ nút tương ứng trên dòng plugin.

## Tự tạo bản mở rộng

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
    build().run(9208)
```

Trang gọi máy chủ của chính plugin bằng `sdk/mo-rong.js`: `import { server } from './mo-rong.js'`, rồi
`await server('api/phieu')`.

Để chạy cùng các plugin khác, cần thêm:
- một dịch vụ trong `deploy/compose.yaml` (chép dịch vụ có sẵn, đổi `PLUGIN`, `PORT`, tên biến, volume);
- cặp biến `<TÊN>_TOKEN`, `<TÊN>_SECRET` trong `deploy/.env.example`.

Cổng trong `base_url`, `server.py` và `compose.yaml` phải trùng nhau. Bản mẫu đang dùng 9201–9207, nên plugin mới bắt
đầu từ 9208.

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
2. Cài thử vào một Desktiny thử nghiệm theo mục [Cài vào Desktiny](#cài-vào-desktiny).
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

## An toàn

Mọi bản mở rộng, kể cả bản bạn tự tạo, đều được hưởng các cơ chế sau của Desktiny và của bộ khung:

- Plugin chỉ có những quyền quản trị viên đã duyệt. Token cài đặt chỉ tới được hồ sơ mà plugin được báo, hoặc hồ sơ
  thuộc quy trình được chọn.
- Trang của plugin chạy trong khung cách ly. Máy chủ plugin xác định người đang xem bằng **token phiên** của Desktiny
  (`GET /plugin/v1/me`). Đường dẫn `admin=True` chỉ nhận phiên từ khung `admin.page` (chỉ người quản lý tổ chức mở
  được).
- Mọi lời Desktiny gọi tới (sự kiện, bước, công cụ trợ lý) đều được kiểm **chữ ký HMAC**. Báo kết quả của bước chạy
  lâu cũng được ký.
- Máy chủ plugin trả mọi lỗi dạng JSON. Lỗi ngoài dự kiến được ghi vào nhật ký của container, không lộ chi tiết ra
  trang. Chỉ đọc `X-Forwarded-For` khi bật `TRUST_PROXY=1` (máy chủ đặt sau reverse proxy).
- Container máy chủ plugin chạy bằng người dùng thường, hệ tệp chỉ đọc, `no-new-privileges`. Gói máy chủ không bao giờ
  chứa `deploy/.env`.
- Gói giao diện là dữ liệu thuần, không chứa mã. Gỡ gói thì Desktiny trở về giao diện và nghiệp vụ mặc định.
- Khung plugin không có hộp thoại `alert/prompt` và không tải tệp về được. Hãy dùng hộp thoại xác nhận của Desktiny
  (`desktiny.confirm`) và hiện nội dung để người dùng sao chép.

## Giới hạn

- **Chấm công GPS** tin vị trí do trình duyệt báo lên, nên người dùng có kỹ thuật có thể làm giả. Trình duyệt chỉ cho
  lấy vị trí khi trang chạy trên HTTPS (trừ `localhost`).
- **Cổng tiếp nhận trực tuyến** lưu số CCCD và số điện thoại không mã hóa, chưa có thời hạn lưu giữ. Cần bổ sung trước
  khi dùng với dữ liệu thật.
- **Ký số** là chữ ký mô phỏng bằng HMAC, không phải chữ ký số có giá trị pháp lý.

## Phát triển và kiểm thử

### Cấu trúc thư mục

```
build.bat, build.sh     nút đóng gói (gọi scripts/dong_goi.py)
scripts/dong_goi.py     kiểm manifest rồi đóng gói vào dist/
expansion/<bản>/        các bản mở rộng (README.md, packs/, plugins/)
lib/mo_rong/            bộ khung máy chủ plugin: định tuyến, kiểm chữ ký, phiên người xem, SQLite, PDF, tiện ích tiếng Việt
lib/desktiny_plugin/    bản sao SDK Python của Desktiny (packages/desktiny-plugin), cập nhật cùng Desktiny
sdk/                    SDK khung của Desktiny, mo-rong.js (trang gọi máy chủ plugin), chung.css
tests/                  test máy chủ plugin (Desktiny giả), test đóng gói, tests/js (Node), tests/desktiny (Desktiny thật)
deploy/                 Dockerfile, compose.yaml, .env.example
```

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

## Đóng góp

Xem [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) và [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Thành phần bên thứ ba (phông chữ) ở [THIRD_PARTY.md](THIRD_PARTY.md).

## Giấy phép

Apache-2.0 (`LICENSE`).
