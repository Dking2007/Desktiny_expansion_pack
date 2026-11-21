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

    python scripts/dong_goi.py [--host plugins.co-quan.vn]      (or build.bat / ./build.sh / make build)
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


def server_files() -> dict[str, bytes]:
    """What the plugin servers need to run: the server kit, the SDK, the connected plugins (same layout), Docker files."""
    _, connected = plugins()
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


def all_problems() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    if not expansions():
        found["expansion/"] = ["Không có bản mở rộng nào (expansion/<tên>/packs, expansion/<tên>/plugins)."]
    for kind, marker in (("packs", "desktiny-pack.json"), ("plugins", "desktiny-plugin.json")):
        twice = [name for name, count in Counter(p.parent.name for p in _found(kind, marker)).items() if count > 1]
        if twice:
            found[f"expansion/*/{kind}"] = [f"Tên trùng giữa các bản mở rộng: {', '.join(sorted(twice))}."]
    if found:
        return found
    for name in packs():
        found[pack_dir(name).relative_to(ROOT).as_posix()] = pack_problems(name)
    packaged, connected = plugins()
    for name in packaged + connected:
        base = plugin_dir(name)
        found[base.relative_to(ROOT).as_posix()] = plugin_problems(read_json(base / "desktiny-plugin.json"),
                                                                   base if name in packaged else None)  # fmt: skip
    return {where: issues for where, issues in found.items() if issues}


# ---- Build -------------------------------------------------------------------------------------------


def guide(built: list[tuple[str, str, str]], host: str | None) -> str:
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
                      "   docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build"]  # fmt: skip
        else:
            lines.append(f"BẢN MỞ RỘNG: {directory}")
        lines += [f"   - {path}   [{kind}] {note}".rstrip() for path, kind, note in rows]
        lines.append("")
    lines += [
        "Plugin kết nối: sau khi Duyệt quyền, Desktiny hiện TOKEN và KHOÁ KÝ một lần — chép vào deploy/.env",
        "(<TÊN>_TOKEN, <TÊN>_SECRET) rồi chạy lại docker compose. Thêm máy chủ plugin vào PLUGIN_ALLOWED_HOSTS",
        "và PLUGIN_FRAME_SOURCES của Desktiny.",
        f"base_url của plugin kết nối: {'trỏ tới ' + host if host else 'http://localhost:92xx (đóng gói lại với --host <máy chủ> khi triển khai thật)'}.",
        "",
        "Chi tiết: README.md của bộ mở rộng.",
    ]  # fmt: skip
    return "\n".join(lines) + "\n"


def build(host: str | None = None, out: Path = DIST) -> list[tuple[str, str, str]]:
    """Check, then write every zip under `out`; returns (path in out, kind, note) for each file."""
    issues = all_problems()
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

    for expansion in expansions():
        for name in packs(expansion):
            data = read_json(pack_dir(name) / "desktiny-pack.json")
            write(f"{expansion}/goi-{name}-{data['version']}.zip", zipped(pack_files(name)), "gói giao diện", data["name"])
        packaged, connected = plugins(expansion)
        for name in packaged + connected:
            data = manifest(name, host)
            files = packaged_plugin_files(name) if name in packaged else connected_plugin_files(name, host)
            kind = "plugin đóng gói, không cần máy chủ" if name in packaged else f"plugin kết nối, máy chủ {data['base_url']}"
            write(f"{expansion}/plugin-{name}-{data['version']}.zip", zipped(files), kind, data["name"])
    _, connected = plugins()
    if connected:
        write(f"{SERVER_DIR}/may-chu-plugin-{project_version()}.zip", zipped(server_files()), "máy chủ",
              f"{len(connected)} plugin kết nối: " + ", ".join(connected))  # fmt: skip
    (out / "HUONG-DAN-CAI.txt").write_text(guide(built, host), encoding="utf-8")
    return built


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # Windows consoles default to a code page without Vietnamese
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", "--base-url-host", dest="host",
                        help="Máy chủ thật của các plugin kết nối, ví dụ plugins.co-quan.vn")  # fmt: skip
    parser.add_argument("--out", type=Path, default=DIST, help="Thư mục kết quả (mặc định dist/).")
    args = parser.parse_args()
    built = build(args.host, args.out)
    for path, kind, note in built:
        print(f"✓ {path}  ({kind})  {note}")
    print(f"\nĐã đóng gói {len(built)} tệp vào {args.out}. Xem {args.out / 'HUONG-DAN-CAI.txt'} để biết cài vào đâu.")


if __name__ == "__main__":
    main()
