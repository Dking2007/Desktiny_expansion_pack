# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Build what an administrator uploads to Desktiny, into dist/:

* packs/<tên>        → dist/goi-<tên>.zip            (Quản trị › Gói giao diện › Tải gói lên)
* packaged plugins   → dist/plugin-<tên>.zip         (Quản trị › Plugin; the frame SDK and shared styles are copied in)
* connected plugins  → dist/plugin-<tên>.json        (the manifest; the plugin's server runs separately)

    python scripts/dong_goi.py [--base-url-host plugins.co-quan.vn]

`--base-url-host` rewrites the connected plugins' `base_url` (http://localhost:92xx) for a real deployment.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SHARED = ["desktiny-plugin-sdk.js", "chung.css"]
SKIP = {"__pycache__", ".pytest_cache", "data"}


def folder(path: Path) -> dict[str, bytes]:
    return {
        file.relative_to(path).as_posix(): file.read_bytes()
        for file in sorted(path.rglob("*"))
        if file.is_file() and not SKIP & set(file.relative_to(path).parts)
    }


def pack_files(name: str) -> dict[str, bytes]:
    return folder(ROOT / "packs" / name)


def packaged_plugin_files(name: str) -> dict[str, bytes]:
    """A packaged plugin's files: its manifest, its pages, and the shared SDK and styles next to them."""
    base = ROOT / "plugins" / name
    files = {"desktiny-plugin.json": (base / "desktiny-plugin.json").read_bytes()}
    files |= {f"ui/{path}": data for path, data in folder(base / "ui").items()}
    for shared in SHARED:
        files[f"ui/{shared}"] = (ROOT / "sdk" / shared).read_bytes()
    if (base / "README.md").is_file():
        files["README.md"] = (base / "README.md").read_bytes()
    return files


def manifest(name: str, host: str | None = None) -> dict:
    data = json.loads((ROOT / "plugins" / name / "desktiny-plugin.json").read_text(encoding="utf-8"))
    if host and data.get("base_url"):
        parts = urlsplit(data["base_url"])
        data["base_url"] = f"https://{host}/{name}" if "." in host else f"{parts.scheme}://{host}:{parts.port}"
    return data


def plugins() -> tuple[list[str], list[str]]:
    """(packaged, connected) plugin folder names."""
    packaged, connected = [], []
    for path in sorted((ROOT / "plugins").iterdir()):
        if (path / "desktiny-plugin.json").is_file():
            (connected if manifest(path.name).get("base_url") else packaged).append(path.name)
    return packaged, connected


def zipped(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, data in files.items():
            archive.writestr(path, data)
    return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url-host", help="Máy chủ thật của các plugin kết nối, ví dụ plugins.co-quan.vn")
    args = parser.parse_args()
    DIST.mkdir(exist_ok=True)
    for pack in sorted(p.name for p in (ROOT / "packs").iterdir() if p.is_dir()):
        (DIST / f"goi-{pack}.zip").write_bytes(zipped(pack_files(pack)))
        print(f"dist/goi-{pack}.zip")
    packaged, connected = plugins()
    for name in packaged:
        (DIST / f"plugin-{name}.zip").write_bytes(zipped(packaged_plugin_files(name)))
        print(f"dist/plugin-{name}.zip")
    for name in connected:
        text = json.dumps(manifest(name, args.base_url_host), ensure_ascii=False, indent=2) + "\n"
        (DIST / f"plugin-{name}.json").write_text(text, encoding="utf-8")
        print(f"dist/plugin-{name}.json")


if __name__ == "__main__":
    main()
