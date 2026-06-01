"""
SQLite-backed invite code quota store.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Iterator


DEFAULT_MAX_USES = int(os.getenv("INVITE_CODE_MAX_USES", "2"))
DEV_CODE = os.getenv("INVITE_DEV_CODE", "").strip()


class InviteCodeStore:
    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or (
            Path(__file__).resolve().parent.parent / "data" / "invite_codes.db"
        )
        self._lock = threading.Lock()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def verify(self, code: str, fingerprint: str, ip: str, user_agent: str) -> dict[str, Any]:
        normalized_code = _normalize_code(code)
        if not normalized_code or not fingerprint:
            return _invalid_quota()

        with self._lock, self._connect() as connection:
            row = self._get_code_row(connection, normalized_code)
            if not row or row["status"] != "active":
                return _invalid_quota()
            quota = _quota_from_row(row)
            if not quota["valid"]:
                return quota
            self._insert_usage_log(
                connection,
                code=normalized_code,
                fingerprint=fingerprint,
                ip=ip,
                user_agent=user_agent,
                result_status="verified",
                request_id=None,
            )
            return quota

    def quota(self, code: str, fingerprint: str) -> dict[str, Any]:
        normalized_code = _normalize_code(code)
        if not normalized_code or not fingerprint:
            return _invalid_quota()

        with self._lock, self._connect() as connection:
            row = self._get_code_row(connection, normalized_code)
            if not row:
                return _invalid_quota()
            return _quota_from_row(row)

    def consume(
        self,
        code: str,
        fingerprint: str,
        ip: str,
        user_agent: str,
        request_id: str,
        result_status: str,
    ) -> dict[str, Any]:
        normalized_code = _normalize_code(code)
        if not normalized_code or not fingerprint or not request_id:
            return _invalid_quota()

        with self._lock, self._connect() as connection:
            row = self._get_code_row(connection, normalized_code)
            if not row or row["status"] != "active":
                return _invalid_quota()

            existing_log = connection.execute(
                """
                SELECT id FROM usage_logs
                WHERE code = ? AND request_id = ? AND result_status = 'success'
                """,
                (normalized_code, request_id),
            ).fetchone()
            if existing_log:
                return _quota_from_row(row)

            quota = _quota_from_row(row)
            if not quota["valid"]:
                self._insert_usage_log(
                    connection,
                    code=normalized_code,
                    fingerprint=fingerprint,
                    ip=ip,
                    user_agent=user_agent,
                    result_status="rejected_quota_exhausted",
                    request_id=request_id,
                )
                return quota

            if result_status == "success" and not bool(row["unlimited"]):
                connection.execute(
                    "UPDATE invite_codes SET used_count = used_count + 1 WHERE code = ?",
                    (normalized_code,),
                )

            self._insert_usage_log(
                connection,
                code=normalized_code,
                fingerprint=fingerprint,
                ip=ip,
                user_agent=user_agent,
                result_status=result_status,
                request_id=request_id,
            )
            updated_row = self._get_code_row(connection, normalized_code)
            return _quota_from_row(updated_row)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS invite_codes (
                    code TEXT PRIMARY KEY,
                    max_uses INTEGER NOT NULL,
                    used_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    unlimited INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    result_status TEXT NOT NULL,
                    request_id TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_success_request
                ON usage_logs(code, request_id, result_status)
                WHERE request_id IS NOT NULL AND result_status = 'success'
                """
            )
            now = _now()
            for code in _load_invite_codes_from_env():
                connection.execute(
                    """
                    INSERT OR IGNORE INTO invite_codes
                    (code, max_uses, used_count, created_at, status, unlimited)
                    VALUES (?, ?, 0, ?, 'active', 0)
                    """,
                    (code, DEFAULT_MAX_USES, now),
                )
            if DEV_CODE:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO invite_codes
                    (code, max_uses, used_count, created_at, status, unlimited)
                    VALUES (?, 0, 0, ?, 'active', 1)
                    """,
                    (DEV_CODE, now),
                )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _get_code_row(self, connection: sqlite3.Connection, code: str) -> sqlite3.Row | None:
        return connection.execute(
            "SELECT * FROM invite_codes WHERE code = ?",
            (code,),
        ).fetchone()

    def _insert_usage_log(
        self,
        connection: sqlite3.Connection,
        code: str,
        fingerprint: str,
        ip: str,
        user_agent: str,
        result_status: str,
        request_id: str | None,
    ) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO usage_logs
            (code, timestamp, ip, fingerprint, user_agent, result_status, request_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (code, _now(), ip, fingerprint, user_agent, result_status, request_id),
        )


def _quota_from_row(row: sqlite3.Row | None) -> dict[str, Any]:
    if not row:
        return _invalid_quota()
    unlimited = bool(row["unlimited"])
    limit = None if unlimited else int(row["max_uses"])
    used = int(row["used_count"])
    remaining = None if unlimited else max(0, int(row["max_uses"]) - used)
    valid = row["status"] == "active" and (unlimited or remaining > 0)
    return {
        "valid": valid,
        "remaining": remaining,
        "limit": limit,
        "used": used,
        "unlimited": unlimited,
    }


def _invalid_quota() -> dict[str, Any]:
    return {
        "valid": False,
        "remaining": 0,
        "limit": DEFAULT_MAX_USES,
        "used": 0,
        "unlimited": False,
    }


def _normalize_code(code: str) -> str:
    return str(code or "").strip()


def _load_invite_codes_from_env() -> list[str]:
    raw_codes = os.getenv("INVITE_CODES", "")
    codes = [
        code.strip()
        for code in raw_codes.replace("\n", ",").split(",")
        if code.strip()
    ]
    return sorted(set(codes))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
