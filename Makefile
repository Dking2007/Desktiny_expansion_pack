# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
PYTHON ?= python3
DESKTINY_DIR ?= ../Desktiny

.PHONY: help test test-js test-desktiny lint dist up
help:
	@echo "test            test máy chủ plugin (Python)"
	@echo "test-js         test mã trang của plugin đóng gói (Node 22)"
	@echo "test-desktiny   cài thật mọi gói và plugin vào Desktiny ở DESKTINY_DIR rồi chạy luồng"
	@echo "lint            ruff"
	@echo "dist            đóng gói vào dist/ (gói .zip, plugin đóng gói .zip, manifest plugin kết nối)"
	@echo "up              chạy máy chủ các plugin kết nối (deploy/compose.yaml, cần deploy/.env)"

test:
	PYTHONPATH=lib $(PYTHON) -m pytest -q tests --ignore=tests/desktiny

test-js:
	node --test tests/js/*.test.mjs

test-desktiny:
	DESKTINY_DIR=$(DESKTINY_DIR) PYTHONPATH=lib $(PYTHON) -m pytest -q tests/desktiny

lint:
	$(PYTHON) -m ruff check .

dist:
	$(PYTHON) scripts/dong_goi.py $(if $(HOST),--base-url-host $(HOST))

up:
	docker compose -f deploy/compose.yaml --env-file deploy/.env up -d --build
