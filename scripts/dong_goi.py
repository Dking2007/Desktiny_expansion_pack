# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Build everything an administrator installs, as .zip files in dist/ (the folder is emptied first).

Sources, one folder per expansion:

    expansion/<bản mở rộng>/packs/<gói>/desktiny-pack.json
    expansion/<bản mở rộng>/plugins/<plugin>/desktiny-plugin.json   (+ server.py for a connected plugin)

Output:

    dist/
      <bản mở rộng>/goi-<gói>-<phiên bản>.zip            Quản trị › Gói giao diện › Tải gói lên
      <bản mở rộng>/plugin-<plugin>-<phiên bản>.zip      Quản trị › Plugin › Cài plugin
      may-chu-plugin/may-chu-plugin-<phiên bản>.zip    servers of every connected plugin (Docker Compose)
      HUONG-DAN-CAI.txt                               what to upload where, in order

* A packaged plugin's zip holds its manifest, its pages and the shared frame SDK and styles.
* A connected plugin's zip holds its manifest only (its pages are served by its own server, at `base_url`);
  `--host` rewrites `base_url` (http://localhost:92xx) for a real deployment.
* Every manifest is checked first with the rules Desktiny applies on upload; nothing is written if one fails.
  Pack and plugin folder names are unique across expansions.

    python scripts/dong_goi.py [TÊN ...] [--chon] [--host plugins.co-quan.vn]   (or build.bat / ./build.sh / make build)

TÊN picks what to build (all by default): an expansion (all of it), a pack or a plugin (`goi-<gói>`, `plugin-<plugin>`
or the bare name). `--chon` asks from a numbered menu instead (build.bat does this when given no arguments).
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
import tomllib
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from desktiny_plugin.cli import problems as plugin_problems  # noqa: E402

DIST = ROOT / "dist"
SERVER_DIR = "may-chu-plugin"
SHARED = ["desktiny-plugin-sdk.js", "chung.css"]
SKIP = {"__pycache__", ".pytest_cache", "data", ".env"}
# Zip entries get a fixed date so the same sources always give the same archive.
STAMP = (2026, 1, 1, 0, 0, 0)


# ---- Sources -----------------------------------------------------------------------------------------


def folder(path: Path) -> dict[str, bytes]:
    return {
        file.relative_to(path).as_posix(): file.read_bytes()
        for file in sorted(path.rglob("*"))
        if file.is_file() and not SKIP & set(file.relative_to(path).parts) and file.suffix not in {".pyc", ".sqlite3"}
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def project_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def expansions() -> list[str]:
    base = ROOT / "expansion"
    return sorted(p.name for p in base.iterdir() if p.is_dir()) if base.is_dir() else []


def _found(kind: str, marker: str) -> list[Path]:
    """Every expansion/*/<kind>/<name> folder that has its manifest, sorted by expansion then name."""
    return [path for expansion in expansions()
            for path in sorted((ROOT / "expansion" / expansion / kind).glob(f"*/{marker}"))]  # fmt: skip


def _dir(kind: str, marker: str, name: str) -> Path:
    for path in _found(kind, marker):
        if path.parent.name == name:
            return path.parent
    raise KeyError(f"Không có {kind[:-1]} “{name}” trong expansion/*/{kind}/.")


def pack_dir(name: str) -> Path:
    return _dir("packs", "desktiny-pack.json", name)


def plugin_dir(name: str) -> Path:
    return _dir("plugins", "desktiny-plugin.json", name)


def expansion_of(path: Path) -> str:
    """expansion/<bản mở rộng>/<packs|plugins>/<tên> → <bản mở rộng>."""
    return path.relative_to(ROOT / "expansion").parts[0]


def packs(expansion: str | None = None) -> list[str]:
    paths = [p.parent for p in _found("packs", "desktiny-pack.json")]
    return [p.name for p in paths if expansion in (None, expansion_of(p))]


def plugins(expansion: str | None = None) -> tuple[list[str], list[str]]:
    """(packaged, connected) plugin folder names; a connected plugin's manifest has `base_url`."""
    packaged, connected = [], []
    for path in (p.parent for p in _found("plugins", "desktiny-plugin.json")):
        if expansion in (None, expansion_of(path)):
            (connected if read_json(path / "desktiny-plugin.json").get("base_url") else packaged).append(path.name)
    return packaged, connected


def pack_files(name: str) -> dict[str, bytes]:
    return folder(pack_dir(name))


def manifest(name: str, host: str | None = None) -> dict:
    """A plugin's manifest; with `host`, a connected plugin's `base_url` points at that server instead."""
    data = read_json(plugin_dir(name) / "desktiny-plugin.json")
    if host and data.get("base_url"):
        parts = urlsplit(data["base_url"])
        # A domain name sits behind a reverse proxy (https, one path per plugin); a bare host keeps the port.
        data["base_url"] = f"https://{host}/{name}" if "." in host else f"{parts.scheme}://{host}:{parts.port}"
    return data


def packaged_plugin_files(name: str) -> dict[str, bytes]:
    """A packaged plugin's files: its manifest, its pages, and the shared SDK and styles next to them."""
    base = plugin_dir(name)
    files = {"desktiny-plugin.json": (base / "desktiny-plugin.json").read_bytes()}
    files |= {f"ui/{path}": data for path, data in folder(base / "ui").items()}
    for shared in SHARED:
        files[f"ui/{shared}"] = (ROOT / "sdk" / shared).read_bytes()
    if (base / "README.md").is_file():
        files["README.md"] = (base / "README.md").read_bytes()
    return files


def connected_plugin_files(name: str, host: str | None = None) -> dict[str, bytes]:
    """A connected plugin's zip: the manifest only; its pages and endpoints live on its server."""
    text = json.dumps(manifest(name, host), ensure_ascii=False, indent=2) + "\n"
    files = {"desktiny-plugin.json": text.encode()}
    if (plugin_dir(name) / "README.md").is_file():
        files["README.md"] = (plugin_dir(name) / "README.md").read_bytes()
    return files


def server_files(connected: list[str] | None = None) -> dict[str, bytes]:
    """What the plugin servers need to run: the server kit, the SDK, the connected plugins (same layout), Docker files."""
    connected = plugins()[1] if connected is None else connected
    files: dict[str, bytes] = {}
    for part in ("lib", "sdk", "deploy"):
        files |= {f"{part}/{path}": data for path, data in folder(ROOT / part).items()}
    for name in connected:
        base = plugin_dir(name)
        prefix = base.relative_to(ROOT).as_posix()
        files |= {f"{prefix}/{path}": data for path, data in folder(base).items()}
    files["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    return files


def zipped(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, data in files.items():
            archive.writestr(zipfile.ZipInfo(path, STAMP), data, zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


# ---- Checks ------------------------------------------------------------------------------------------


def pack_problems(name: str) -> list[str]:
    """What is missing or broken in a pack: its manifest fields and every file it points to."""
    base = pack_dir(name)
    try:
        data = read_json(base / "desktiny-pack.json")
    except ValueError as exc:
        return [f"desktiny-pack.json không đọc được: {exc}"]
    found = [f"Thiếu `{key}`." for key in ("id", "name", "version") if not data.get(key)]
    if data.get("schema") != "desktiny-pack/1":
        found.append("`schema` phải là desktiny-pack/1.")
    appearance = data.get("appearance") or {}
    paths = [appearance[key] for key in ("logo", "favicon") if appearance.get(key)]
    paths += [*data.get("processes", []), *data.get("templates", []), *data.get("knowledge", [])]
    for path in paths:
        target = base / path
        if not target.is_file():
            found.append(f"Không có tệp {path}.")
        elif target.suffix == ".json":
            try:
                read_json(target)
            except ValueError as exc:
                found.append(f"{path} không phải JSON hợp lệ: {exc}")
    return found


def layout_problems() -> dict[str, list[str]]:
    """No expansion at all, or a pack/plugin name used by two expansions (names must pick one folder)."""
    found: dict[str, list[str]] = {}
    if not expansions():
        found["expansion/"] = ["Không có bản mở rộng nào (expansion/<tên>/packs, expansion/<tên>/plugins)."]
    for kind, marker in (("packs", "desktiny-pack.json"), ("plugins", "desktiny-plugin.json")):
        twice = [name for name, count in Counter(p.parent.name for p in _found(kind, marker)).items() if count > 1]
        if twice:
            found[f"expansion/*/{kind}"] = [f"Tên trùng giữa các bản mở rộng: {', '.join(sorted(twice))}."]
    return found


def all_problems(chosen: Selection | None = None) -> dict[str, list[str]]:
    """What stops the build, for the chosen packs and plugins (all of them by default)."""
    found = layout_problems()
    if found:
        return found
    chosen = chosen or select()
    for name in chosen.packs:
        found[pack_dir(name).relative_to(ROOT).as_posix()] = pack_problems(name)
    packaged = plugins()[0]
    for name in chosen.plugins:
        base = plugin_dir(name)
        found[base.relative_to(ROOT).as_posix()] = plugin_problems(read_json(base / "desktiny-plugin.json"),
                                                                   base if name in packaged else None)  # fmt: skip
    return {where: issues for where, issues in found.items() if issues}


# ---- Choosing ----------------------------------------------------------------------------------------


@dataclass
class Item:
    kind: str  # "goi" or "plugin"
    name: str
    expansion: str
    title: str


@dataclass
class Selection:
    packs: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)


def catalog() -> list[Item]:
    """Everything that can be built, expansion by expansion: its packs, then its plugins."""
    items = []
    for expansion in expansions():
        items += [Item("goi", name, expansion, read_json(pack_dir(name) / "desktiny-pack.json").get("name", name))
                  for name in packs(expansion)]  # fmt: skip
        packaged, connected = plugins(expansion)
        items += [Item("plugin", name, expansion, manifest(name).get("name", name)) for name in packaged + connected]
    return items


def select(choices: list[str] | None = None) -> Selection:
    """The packs and plugins named by `choices` (all when empty). A choice is a number from the menu, an expansion
    (all of it), `goi-<gói>` / `plugin-<plugin>`, or a bare pack or plugin name; commas and spaces separate them."""
    items = catalog()
    words = [w for choice in choices or [] for w in choice.replace(",", " ").split()]
    if not words:
        chosen = items
    else:
        chosen, unknown = [], []
        for word in words:
            word = word.strip().lower().removesuffix(".zip")
            if word.isdigit() and 1 <= int(word) <= len(items):
                found = [items[int(word) - 1]]
            elif word in expansions():
                found = [item for item in items if item.expansion == word]
            else:
                found = [item for item in items if word in (item.name, f"{item.kind}-{item.name}")]
            chosen += found
            unknown += [] if found else [word]
        if unknown:
            names = ", ".join([*expansions(), *(item.name for item in items)])
            raise SystemExit(f"✗ Không có: {', '.join(unknown)}. Chọn trong: {names}.")
    picked = [item for item in items if item in chosen]  # catalog order, once each
    return Selection([i.name for i in picked if i.kind == "goi"], [i.name for i in picked if i.kind == "plugin"])


def ask() -> list[str]:
    """The menu shown by build.bat: numbered packs and plugins per expansion; Enter alone builds everything."""
    _, connected = plugins()
    print("Chọn những gì cần đóng gói:\n")
    expansion = None
    for number, item in enumerate(catalog(), 1):
        if item.expansion != expansion:
            expansion = item.expansion
            print(f"  Bản mở rộng {expansion}  (gõ “{expansion}” để lấy cả bản)")
        kind = "gói giao diện" if item.kind == "goi" else ("plugin kết nối" if item.name in connected else "plugin đóng gói")
        print(f"   {number:>2}. {item.title}  [{kind}, {item.name}]")
    try:
        answer = input("\nNhập số hoặc tên, cách nhau bởi dấu cách (Enter = tất cả): ")
    except EOFError:
        answer = ""
    print()
    return [answer]


# ---- Build -------------------------------------------------------------------------------------------


def guide(built: list[tuple[str, str, str]], host: str | None, services: list[str]) -> str:
    """HUONG-DAN-CAI.txt: each file and where it goes, in the order to install them."""
    lines = ["BỘ MỞ RỘNG DESKTINY — CÁC TỆP CẦN CÀI", "=" * 40, "",
             "Mỗi thư mục là một bản mở rộng. Cài gói giao diện trước, rồi plugin:",
             "  goi-*.zip     Quản trị › Gói giao diện › Tải gói lên → xem trước → cài → Dùng giao diện này",
             "  plugin-*.zip  Quản trị › Plugin › Cài plugin → chọn tệp .zip → Duyệt quyền", ""]  # fmt: skip
    for directory in [*expansions(), SERVER_DIR]:
        rows = [(path, kind, note) for path, kind, note in built if path.startswith(directory + "/")]
        if not rows:
            continue
        if directory == SERVER_DIR:
            lines += ["MÁY CHỦ PLUGIN KẾT NỐI — giải nén trên máy chủ, điền deploy/.env, chạy:",
                      "   docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build " + " ".join(services)]  # fmt: skip
        else:
            lines.append(f"BẢN MỞ RỘNG: {directory}")
        lines += [f"   - {path}   [{kind}] {note}".rstrip() for path, kind, note in rows]
        lines.append("")
    if services:
        lines += [
            "Plugin kết nối: sau khi Duyệt quyền, Desktiny hiện TOKEN và KHOÁ KÝ một lần — chép vào deploy/.env",
            "(<TÊN>_TOKEN, <TÊN>_SECRET) rồi chạy lại docker compose. Thêm máy chủ plugin vào PLUGIN_ALLOWED_HOSTS",
            "và PLUGIN_FRAME_SOURCES của Desktiny.",
            f"base_url của plugin kết nối: {'trỏ tới ' + host if host else 'http://localhost:92xx (đóng gói lại với --host <máy chủ> khi triển khai thật)'}.",
            "",
        ]  # fmt: skip
    lines.append("Chi tiết: README.md của bộ mở rộng.")
    return "\n".join(lines) + "\n"


def build(host: str | None = None, out: Path = DIST, only: list[str] | None = None) -> list[tuple[str, str, str]]:
    """Check, then write the zips of the chosen packs and plugins (`only`, see `select`; all by default) under `out`;
    returns (path in out, kind, note) for each file."""
    issues = layout_problems()
    chosen = None if issues else select(only)
    issues = issues or all_problems(chosen)
    if issues:
        message = "\n".join(f"  {where}: {issue}" for where, found in issues.items() for issue in found)
        raise SystemExit(f"✗ Chưa đóng gói được, cần sửa:\n{message}")
    if out.exists():
        shutil.rmtree(out)
    built: list[tuple[str, str, str]] = []

    def write(path: str, data: bytes, kind: str, note: str = ""):
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_bytes(data)
        built.append((path, kind, note))

    for name in chosen.packs:
        data = read_json(pack_dir(name) / "desktiny-pack.json")
        write(f"{expansion_of(pack_dir(name))}/goi-{name}-{data['version']}.zip", zipped(pack_files(name)),
              "gói giao diện", data["name"])  # fmt: skip
    packaged = plugins()[0]
    servers = [name for name in chosen.plugins if name not in packaged]
    for name in chosen.plugins:
        data = manifest(name, host)
        files = packaged_plugin_files(name) if name in packaged else connected_plugin_files(name, host)
        kind = "plugin đóng gói, không cần máy chủ" if name in packaged else f"plugin kết nối, máy chủ {data['base_url']}"
        write(f"{expansion_of(plugin_dir(name))}/plugin-{name}-{data['version']}.zip", zipped(files), kind, data["name"])
    if servers:
        write(f"{SERVER_DIR}/may-chu-plugin-{project_version()}.zip", zipped(server_files(servers)), "máy chủ",
              f"{len(servers)} plugin kết nối: " + ", ".join(servers))  # fmt: skip
    (out / "HUONG-DAN-CAI.txt").write_text(guide(built, host, servers), encoding="utf-8")
    return built


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # Windows consoles default to a code page without Vietnamese
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chon", nargs="*", metavar="TÊN",
                        help="Chỉ đóng gói những thứ này: bản mở rộng (cả bản), gói, plugin (vd. nhan-su ky-so). "
                             "Bỏ trống = tất cả.")  # fmt: skip
    parser.add_argument("--chon", dest="menu", action="store_true", help="Hiện danh sách để chọn (build.bat dùng).")
    parser.add_argument("--host", "--base-url-host", dest="host",
                        help="Máy chủ thật của các plugin kết nối, ví dụ plugins.co-quan.vn")  # fmt: skip
    parser.add_argument("--out", type=Path, default=DIST, help="Thư mục kết quả (mặc định dist/).")
    args = parser.parse_args()
    only = args.chon
    if args.menu and not only and not layout_problems():
        only = ask()
    built = build(args.host, args.out, only)
    for path, kind, note in built:
        print(f"✓ {path}  ({kind})  {note}")
    print(f"\nĐã đóng gói {len(built)} tệp vào {args.out}. Xem {args.out / 'HUONG-DAN-CAI.txt'} để biết cài vào đâu.")


if __name__ == "__main__":
    main()
