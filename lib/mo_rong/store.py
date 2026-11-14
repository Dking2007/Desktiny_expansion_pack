# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
"""The plugin's own data, in one SQLite file: Desktiny never holds a sector's records for it."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path: Path | str, schema: str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        # One connection, used under a lock: plugin traffic is small and this keeps writes in order.
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.lock = threading.RLock()
        with self.lock:
            self.db.executescript(schema)

    @contextmanager
    def transaction(self):
        """BEGIN IMMEDIATE … COMMIT: numbers handed out inside are never handed out twice."""
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            self.db.execute("COMMIT")

    def all(self, sql: str, *args) -> list[dict]:
        with self.lock:
            return [dict(row) for row in self.db.execute(sql, args)]

    def one(self, sql: str, *args) -> dict | None:
        with self.lock:
            row = self.db.execute(sql, args).fetchone()
            return dict(row) if row else None

    def run(self, sql: str, *args) -> int:
        with self.lock:
            return self.db.execute(sql, args).lastrowid
