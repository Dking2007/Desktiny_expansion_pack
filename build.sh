#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
# Đóng gói mọi gói giao diện và plugin thành .zip trong dist/:  ./build.sh [--host plugins.co-quan.vn]
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
exec "$PY" scripts/dong_goi.py "$@"
