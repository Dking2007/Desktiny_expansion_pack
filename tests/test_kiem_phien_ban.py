# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import kiem_phien_ban as kp  # noqa: E402


def test_every_manifest_and_the_repo_use_semver():
    assert kp.format_problems() == []


@pytest.mark.parametrize(
    ("changed", "old", "new", "ok"),
    [
        (True, "1.1.0", "1.1.0", False),  # nội dung đổi, số giữ nguyên: hai .zip cùng tên khác nội dung
        (True, "1.1.0", "1.1.1", True),
        (True, "1.1.0", "1.0.9", False),  # lùi số
        (False, "1.1.0", "1.1.0", True),
        (False, "1.1.0", "1.0.0", False),
        (True, None, "1.0.0", True),  # gói hoặc plugin mới
    ],
)
def test_component_step(changed, old, new, ok):
    assert (kp.component_problem("plugin x", changed, old, new) is None) == ok


@pytest.mark.parametrize(
    ("old", "new", "ok"),
    [
        ("1.1.0", "1.1.1", True),
        ("1.1.0", "1.2.0", True),
        ("1.1.0", "2.0.0", True),
        ("1.1.0", "1.1.0", False),
        ("1.1.0", "1.2.1", False),
        ("1.1.0", "2.1.0", False),
    ],
)
def test_repo_step(old, new, ok):
    assert (kp.repo_problem(old, new) is None) == ok
