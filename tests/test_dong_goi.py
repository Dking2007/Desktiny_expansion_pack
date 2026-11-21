# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""The build: per expansion one .zip per pack and per plugin, a server bundle, an install guide; nothing if a
manifest is wrong."""

import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dong_goi  # noqa: E402


def names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def read(path: Path, member: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(member))


def test_each_expansion_gets_its_pack_and_plugins_as_zips_with_an_install_guide(tmp_path):
    out = tmp_path / "dist"
    (out / "cu.txt").parent.mkdir()
    (out / "cu.txt").write_text("bản cũ", encoding="utf-8")
    built = dong_goi.build(out=out)
    paths = {path for path, _, _ in built}
    assert not (out / "cu.txt").exists()  # the folder is emptied first
    assert dong_goi.expansions() == ["mot-cua-xa", "nhan-su"]
    assert {
        "nhan-su/goi-nhan-su-1.0.0.zip", "nhan-su/plugin-cham-cong-1.0.0.zip", "nhan-su/plugin-luong-kpi-1.0.0.zip",
        "nhan-su/plugin-nhac-han-1.0.0.zip", "mot-cua-xa/goi-mot-cua-xa-1.0.0.zip", "mot-cua-xa/plugin-so-van-ban-1.0.0.zip",
        "mot-cua-xa/plugin-ky-so-1.0.0.zip", "mot-cua-xa/plugin-tiep-nhan-1.0.0.zip", "mot-cua-xa/plugin-tinh-han-1.0.0.zip",
        "mot-cua-xa/plugin-doc-giay-to-1.0.0.zip", "may-chu-plugin/may-chu-plugin-1.0.0.zip",
    } == paths  # fmt: skip
    guide = (out / "HUONG-DAN-CAI.txt").read_text(encoding="utf-8")
    assert all(path in guide for path in paths)

    pack = out / "mot-cua-xa/goi-mot-cua-xa-1.0.0.zip"
    assert {"desktiny-pack.json", "assets/logo.svg", "processes/khai-sinh.json"} <= names(pack)
    tinh_han = names(out / "mot-cua-xa/plugin-tinh-han-1.0.0.zip")
    assert {"desktiny-plugin.json", "ui/tinh-han.html", "ui/desktiny-plugin-sdk.js", "ui/chung.css"} <= tinh_han
    # A connected plugin's zip is its manifest; its server is in the server bundle, in the same layout as here.
    assert names(out / "mot-cua-xa/plugin-so-van-ban-1.0.0.zip") == {"desktiny-plugin.json"}
    server = names(out / "may-chu-plugin/may-chu-plugin-1.0.0.zip")
    assert {"lib/mo_rong/server.py", "deploy/compose.yaml", "deploy/Dockerfile",
            "expansion/mot-cua-xa/plugins/so-van-ban/server.py", "expansion/nhan-su/plugins/cham-cong/server.py"} <= server  # fmt: skip
    assert not any("tinh-han" in path or "packs/" in path for path in server)
    assert not any("__pycache__" in path or path == "deploy/.env" for path in server)


def test_the_same_sources_give_the_same_zip(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    dong_goi.build(out=first)
    dong_goi.build(out=second)
    for path in first.rglob("*.zip"):
        assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()


def test_host_points_connected_plugins_at_the_real_server(tmp_path):
    dong_goi.build("plugins.co-quan.vn", out=tmp_path)
    data = read(tmp_path / "mot-cua-xa/plugin-ky-so-1.0.0.zip", "desktiny-plugin.json")
    assert data["base_url"] == "https://plugins.co-quan.vn/ky-so"
    assert dong_goi.manifest("ky-so", "10.0.0.5")["base_url"] == "https://10.0.0.5/ky-so"  # dotted: proxied
    assert dong_goi.manifest("ky-so", "may-chu")["base_url"] == "http://may-chu:9204"
    assert "base_url" not in read(tmp_path / "mot-cua-xa/plugin-tinh-han-1.0.0.zip", "desktiny-plugin.json")


def fake_root(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "goc"
    for part in ("sdk", "lib", "deploy"):
        (root / part).mkdir(parents=True)
    monkeypatch.setattr(dong_goi, "ROOT", root)
    return root


def write_pack(folder: Path, **fields):
    folder.mkdir(parents=True)
    data = {"schema": "desktiny-pack/1", "id": "vn.thu.goi", "name": "Thử", "version": "1.0.0", **fields}
    (folder / "desktiny-pack.json").write_text(json.dumps(data), encoding="utf-8")


def test_a_broken_pack_stops_the_build(tmp_path, monkeypatch):
    root = fake_root(tmp_path, monkeypatch)
    write_pack(root / "expansion/thu/packs/thu", processes=["processes/mat.json"])
    assert dong_goi.pack_problems("thu") == ["Không có tệp processes/mat.json."]
    with pytest.raises(SystemExit, match="mat.json"):
        dong_goi.build(out=tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_the_same_name_in_two_expansions_stops_the_build(tmp_path, monkeypatch):
    root = fake_root(tmp_path, monkeypatch)
    write_pack(root / "expansion/mot/packs/chung")
    write_pack(root / "expansion/hai/packs/chung")
    with pytest.raises(SystemExit, match="trùng.*chung"):
        dong_goi.build(out=tmp_path / "dist")
