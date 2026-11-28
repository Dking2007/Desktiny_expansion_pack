# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""Kiểm số phiên bản theo SemVer (MAJOR.MINOR.PATCH) trước khi phát hành.

  python scripts/kiem_phien_ban.py                              kho và mọi manifest đúng dạng X.Y.Z
  python scripts/kiem_phien_ban.py --tag v1.2.0                 + tag khớp pyproject.toml, CHANGELOG có mục [1.2.0] - ngày
  python scripts/kiem_phien_ban.py --tag v1.2.0 --since v1.1.0  + gói, plugin nào đổi nội dung thì đã tăng version

Tên tệp .zip lấy theo `version` trong manifest, nên đổi nội dung mà giữ số sẽ tạo hai tệp cùng tên khác nội dung.
Nội dung một plugin đóng gói gồm cả SDK dùng chung trong sdk/.
"""

import argparse
import re
import subprocess
import sys

import dong_goi

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse(version: str | None) -> tuple[int, int, int] | None:
    match = SEMVER.match(version or "")
    return tuple(int(x) for x in match.groups()) if match else None


def components() -> list[tuple[str, str, list[str]]]:
    """(label, manifest path, paths whose change changes its .zip), relative to the repo."""
    packaged, connected = dong_goi.plugins()
    rel = lambda p: p.relative_to(dong_goi.ROOT).as_posix()  # noqa: E731
    out = []
    for name in dong_goi.packs():
        d = dong_goi.pack_dir(name)
        out.append((f"gói {name}", f"{rel(d)}/desktiny-pack.json", [rel(d)]))
    for name in packaged + connected:
        d = dong_goi.plugin_dir(name)
        watched = [rel(d)] + (["sdk"] if name in packaged else [])
        out.append((f"plugin {name}", f"{rel(d)}/desktiny-plugin.json", watched))
    return out


def format_problems() -> list[str]:
    problems = (
        []
        if parse(dong_goi.project_version())
        else [f"pyproject.toml: “{dong_goi.project_version()}” không đúng dạng X.Y.Z"]
    )
    for label, manifest, _ in components():
        version = dong_goi.read_json(dong_goi.ROOT / manifest).get("version")
        if not parse(version):
            problems.append(f"{label}: “{version}” không đúng dạng X.Y.Z")
    return problems


def component_problem(label: str, changed: bool, old: str | None, new: str) -> str | None:
    if old is None:
        return None
    if parse(new) < parse(old):
        return f"{label}: {old} → {new} lùi số"
    if changed and parse(new) == parse(old):
        return f"{label}: nội dung đổi từ bản trước nhưng version vẫn {new}"
    return None


def repo_problem(old: str, new: str) -> str | None:
    a, b = parse(old), parse(new)
    if b <= a:
        return f"kho: {new} không lớn hơn {old}"
    if b[0] > a[0] and b[1:] != (0, 0):
        return f"kho: {new} tăng MAJOR thì MINOR và PATCH phải về 0"
    if b[0] == a[0] and b[1] > a[1] and b[2] != 0:
        return f"kho: {new} tăng MINOR thì PATCH phải về 0"
    return None


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(dong_goi.ROOT), *args], capture_output=True, text=True, encoding="utf-8"
    )


def since_problems(previous: str) -> list[str]:
    problems = []
    old_repo = re.search(r'^version = "([^"]+)"', _git("show", f"{previous}:pyproject.toml").stdout, re.M)
    if old_repo and (problem := repo_problem(old_repo.group(1), dong_goi.project_version())):
        problems.append(problem)
    for label, manifest, watched in components():
        shown = _git("show", f"{previous}:{manifest}")
        old = (
            re.search(r'"version"\s*:\s*"([^"]+)"', shown.stdout).group(1) if shown.returncode == 0 else None
        )
        changed = _git("diff", "--quiet", previous, "--", *watched).returncode != 0
        new = dong_goi.read_json(dong_goi.ROOT / manifest)["version"]
        if problem := component_problem(label, changed, old, new):
            problems.append(problem)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tag", help="tag sắp phát hành, ví dụ v1.2.0")
    parser.add_argument("--since", help="tag phát hành trước đó, ví dụ v1.1.0")
    args = parser.parse_args()

    version = dong_goi.project_version()
    problems = format_problems()
    if args.tag:
        if args.tag != f"v{version}":
            problems.append(f"Tag {args.tag} khác phiên bản trong pyproject.toml v{version}")
        changelog = (dong_goi.ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        if not re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.M):
            problems.append(f"CHANGELOG.md thiếu mục “## [{version}] - YYYY-MM-DD”")
    if args.since:
        problems += since_problems(args.since)
    for problem in problems:
        print(f"LỖI: {problem}", file=sys.stderr)
    if not problems:
        print(f"Phiên bản kho {version}: {len(components())} gói và plugin đúng dạng"
              + (f", đã tăng số đủ so với {args.since}" if args.since else ""))  # fmt: skip
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
