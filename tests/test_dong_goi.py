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
    assert dong_goi.expansions() == ["mot-cua-xa", "nhan-su", "van-thu"]
    assert {
        "nhan-su/goi-nhan-su-1.1.0.zip", "nhan-su/plugin-cham-cong-1.0.0.zip", "nhan-su/plugin-luong-kpi-1.0.0.zip",
        "nhan-su/plugin-nhac-han-1.0.0.zip", "mot-cua-xa/goi-mot-cua-xa-1.1.0.zip", "mot-cua-xa/plugin-so-van-ban-1.0.0.zip",
        "mot-cua-xa/plugin-ky-so-1.0.0.zip", "mot-cua-xa/plugin-tiep-nhan-1.0.0.zip", "mot-cua-xa/plugin-tinh-han-1.0.0.zip",
        "mot-cua-xa/plugin-doc-giay-to-1.0.0.zip", "van-thu/goi-van-thu-1.0.0.zip", "van-thu/plugin-so-van-ban-den-1.0.0.zip",
        # Văn thư borrows these from Một cửa: the same zips are also in its own folder.
        "van-thu/plugin-so-van-ban-1.0.0.zip", "van-thu/plugin-ky-so-1.0.0.zip", "van-thu/plugin-tinh-han-1.0.0.zip",
        "may-chu-plugin/may-chu-plugin-1.1.0.zip",
    } == paths  # fmt: skip
    guide = (out / "HUONG-DAN-CAI.txt").read_text(encoding="utf-8")
    assert all(path in guide for path in paths)

    pack = out / "mot-cua-xa/goi-mot-cua-xa-1.1.0.zip"
    assert {"desktiny-pack.json", "assets/logo.svg", "processes/khai-sinh.json"} <= names(pack)
    tinh_han = names(out / "mot-cua-xa/plugin-tinh-han-1.0.0.zip")
    assert {"desktiny-plugin.json", "ui/tinh-han.html", "ui/desktiny-plugin-sdk.js", "ui/chung.css"} <= tinh_han
    # A connected plugin's zip is its manifest; its server is in the server bundle, in the same layout as here.
    assert names(out / "mot-cua-xa/plugin-so-van-ban-1.0.0.zip") == {"desktiny-plugin.json"}
    server = names(out / "may-chu-plugin/may-chu-plugin-1.1.0.zip")
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


def test_only_the_chosen_packs_and_plugins_are_built(tmp_path):
    built = {path for path, _, _ in dong_goi.build(out=tmp_path, only=["tinh-han", "plugin-cham-cong, ky-so"])}
    assert built == {"mot-cua-xa/plugin-tinh-han-1.0.0.zip", "nhan-su/plugin-cham-cong-1.0.0.zip",
                     "mot-cua-xa/plugin-ky-so-1.0.0.zip", "may-chu-plugin/may-chu-plugin-1.1.0.zip"}  # fmt: skip
    # The server bundle holds only the chosen connected plugins, and the guide starts just those services.
    server = names(tmp_path / "may-chu-plugin/may-chu-plugin-1.1.0.zip")
    assert "expansion/nhan-su/plugins/cham-cong/server.py" in server and "expansion/mot-cua-xa/plugins/ky-so/server.py" in server
    assert not any("so-van-ban" in path or "luong-kpi" in path for path in server)
    assert "up -d --build ky-so cham-cong" in (tmp_path / "HUONG-DAN-CAI.txt").read_text(encoding="utf-8")


def test_an_expansion_name_takes_all_of_it_and_goi_takes_only_the_pack(tmp_path):
    whole = dong_goi.select(["nhan-su"])
    assert whole.packs == ["nhan-su"] and whole.plugins == ["cham-cong", "luong-kpi", "nhac-han"]
    assert dong_goi.select(["goi-nhan-su"]).plugins == []
    # Packaged plugins only: no server bundle, no docker lines in the guide.
    built = {path for path, _, _ in dong_goi.build(out=tmp_path, only=["goi-mot-cua-xa", "doc-giay-to"])}
    assert built == {"mot-cua-xa/goi-mot-cua-xa-1.1.0.zip", "mot-cua-xa/plugin-doc-giay-to-1.0.0.zip"}
    assert "docker" not in (tmp_path / "HUONG-DAN-CAI.txt").read_text(encoding="utf-8")


def test_a_borrowing_expansion_builds_complete_without_opening_the_lenders_folder(tmp_path):
    chosen = dong_goi.select(["van-thu"])
    assert chosen.packs == ["van-thu"] and chosen.folders == ["van-thu"]
    assert set(chosen.plugins) == {"so-van-ban", "ky-so", "tinh-han", "so-van-ban-den"}
    built = {path for path, _, _ in dong_goi.build(out=tmp_path, only=["van-thu"])}
    assert all(path.startswith(("van-thu/", "may-chu-plugin/")) for path in built)
    assert (tmp_path / "van-thu/plugin-ky-so-1.0.0.zip").read_bytes() == dong_goi.zipped(dong_goi.connected_plugin_files("ky-so"))
    server = names(tmp_path / "may-chu-plugin/may-chu-plugin-1.1.0.zip")
    assert {"expansion/van-thu/plugins/so-van-ban-den/server.py", "expansion/mot-cua-xa/plugins/ky-so/server.py"} <= server
    # Building a lender's plugin on its own puts it in the lender's folder only.
    assert {p for p, _, _ in dong_goi.build(out=tmp_path, only=["ky-so"])} == {
        "mot-cua-xa/plugin-ky-so-1.0.0.zip", "may-chu-plugin/may-chu-plugin-1.1.0.zip"}  # fmt: skip


def test_menu_numbers_follow_the_catalog_and_unknown_names_are_refused(tmp_path):
    items = dong_goi.catalog()
    assert [i.name for i in items[:2]] == ["mot-cua-xa", "doc-giay-to"]  # expansion by expansion, pack first
    number = next(n for n, item in enumerate(items, 1) if item.name == "so-van-ban")
    assert dong_goi.select([f"{number} so-van-ban"]).plugins == ["so-van-ban"]  # once, even if chosen twice
    with pytest.raises(SystemExit, match="Không có: khong-co"):
        dong_goi.build(out=tmp_path / "dist", only=["khong-co"])
    assert not (tmp_path / "dist").exists()


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


def test_borrowing_a_plugin_that_is_not_elsewhere_stops_the_build(tmp_path, monkeypatch):
    root = fake_root(tmp_path, monkeypatch)
    write_pack(root / "expansion/mot/packs/mot")
    (root / "expansion/mot/dung-chung.json").write_text('{"plugins": ["khong-co"]}', encoding="utf-8")
    with pytest.raises(SystemExit, match="khong-co"):
        dong_goi.build(out=tmp_path / "dist")


def test_the_same_name_in_two_expansions_stops_the_build(tmp_path, monkeypatch):
    root = fake_root(tmp_path, monkeypatch)
    write_pack(root / "expansion/mot/packs/chung")
    write_pack(root / "expansion/hai/packs/chung")
    with pytest.raises(SystemExit, match="trùng.*chung"):
        dong_goi.build(out=tmp_path / "dist")
