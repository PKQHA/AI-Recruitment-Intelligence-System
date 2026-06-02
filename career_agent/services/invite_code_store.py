"""
SQLite-backed invite code quota store.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def _get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        import streamlit as st
    except ModuleNotFoundError:
        return default

    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default

    return str(value)


def _get_int_setting(name: str, default: int) -> int:
    raw_value = _get_setting(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(1, value)


DEFAULT_MAX_USES = _get_int_setting("INVITE_CODE_MAX_USES", 2)
DEV_CODE = _get_setting("INVITE_DEV_CODE", "").strip()


class InviteCodeStore:
    def __init__(self, database_path: Path | None = None) -> None:
        self._database_path = database_path or _default_database_path()
        self._lock = threading.Lock()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def verify(self, code: str, fingerprint: str, ip: str, user_agent: str) -> dict[str, Any]:
        normalized_code = _normalize_code(code)
        normalized_fingerprint = _normalize_code(fingerprint)
        if not normalized_code or not normalized_fingerprint:
            with self._lock, self._connect() as connection:
                self._print_current_code_state(connection)
            return _invalid_quota()

        with self._lock, self._connect() as connection:
            row = self._get_code_row(connection, normalized_code)
            if not row or row["status"] != "active":
                self._print_current_code_state(connection)
                return _invalid_quota()

            quota = _quota_from_row(row)
            if not quota["valid"]:
                self._insert_usage_log(
                    connection,
                    code=normalized_code,
                    fingerprint=normalized_fingerprint,
                    ip=ip,
                    user_agent=user_agent,
                    result_status="rejected_quota_exhausted",
                    request_id=None,
                )
                self._print_current_code_state(connection)
                return quota

            self._insert_usage_log(
                connection,
                code=normalized_code,
                fingerprint=normalized_fingerprint,
                ip=ip,
                user_agent=user_agent,
                result_status="verified",
                request_id=None,
            )
            self._print_current_code_state(connection)
            return quota

    def quota(self, code: str, fingerprint: str) -> dict[str, Any]:
        normalized_code = _normalize_code(code)
        normalized_fingerprint = _normalize_code(fingerprint)
        if not normalized_code or not normalized_fingerprint:
            return _invalid_quota()

        with self._lock, self._connect() as connection:
            row = self._get_code_row(connection, normalized_code)
            if not row or row["status"] != "active":
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
        normalized_fingerprint = _normalize_code(fingerprint)
        normalized_request_id = _normalize_code(request_id)
        if not normalized_code or not normalized_fingerprint or not normalized_request_id:
            with self._lock, self._connect() as connection:
                self._print_current_code_state(connection)
            return _invalid_quota()

        with self._lock, self._connect() as connection:
            row = self._get_code_row(connection, normalized_code)
            if not row or row["status"] != "active":
                self._print_current_code_state(connection)
                return _invalid_quota()

            existing_log = connection.execute(
                """
                SELECT id FROM usage_logs
                WHERE code = ? AND request_id = ? AND result_status = 'success'
                """,
                (normalized_code, normalized_request_id),
            ).fetchone()
            if existing_log:
                self._print_current_code_state(connection)
                return _quota_from_row(row)

            quota = _quota_from_row(row)
            if not quota["valid"]:
                self._insert_usage_log(
                    connection,
                    code=normalized_code,
                    fingerprint=normalized_fingerprint,
                    ip=ip,
                    user_agent=user_agent,
                    result_status="rejected_quota_exhausted",
                    request_id=normalized_request_id,
                )
                self._print_current_code_state(connection)
                return quota

            if result_status == "success" and not bool(row["unlimited"]):
                connection.execute(
                    """
                    UPDATE invite_codes
                    SET used_count = used_count + 1
                    WHERE code = ?
                      AND status = 'active'
                      AND unlimited = 0
                      AND used_count < max_uses
                    """,
                    (normalized_code,),
                )

            self._insert_usage_log(
                connection,
                code=normalized_code,
                fingerprint=normalized_fingerprint,
                ip=ip,
                user_agent=user_agent,
                result_status=result_status,
                request_id=normalized_request_id,
            )
            updated_row = self._get_code_row(connection, normalized_code)
            updated_quota = _quota_from_row(updated_row)
            self._print_current_code_state(connection)
            return updated_quota

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
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
            self._sync_configured_codes(connection)

    def _sync_configured_codes(self, connection: sqlite3.Connection) -> None:
        now = _now()
        unlimited_codes = set(_load_unlimited_invite_codes())
        if DEV_CODE:
            unlimited_codes.add(DEV_CODE)

        for code in _load_invite_codes_from_env():
            if code in unlimited_codes:
                continue
            self._upsert_configured_code(
                connection,
                code=code,
                max_uses=DEFAULT_MAX_USES,
                unlimited=False,
                created_at=now,
            )

        for code in unlimited_codes:
            self._upsert_configured_code(
                connection,
                code=code,
                max_uses=0,
                unlimited=True,
                created_at=now,
            )

    def _upsert_configured_code(
        self,
        connection: sqlite3.Connection,
        code: str,
        max_uses: int,
        unlimited: bool,
        created_at: str,
    ) -> None:
        row = self._get_code_row(connection, code)
        if not row:
            connection.execute(
                """
                INSERT INTO invite_codes
                (code, max_uses, used_count, created_at, status, unlimited)
                VALUES (?, ?, 0, ?, 'active', ?)
                """,
                (code, max_uses, created_at, int(unlimited)),
            )
            return

        connection.execute(
            """
            UPDATE invite_codes
            SET max_uses = ?,
                status = 'active',
                unlimited = ?
            WHERE code = ?
            """,
            (max_uses, int(unlimited), code),
        )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
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

    def _print_current_code_state(self, connection: sqlite3.Connection) -> None:
        print("CURRENT CODE STATE:", _code_state_snapshot(connection))


def _default_database_path() -> Path:
    configured_path = _get_setting("INVITE_CODE_DB_PATH", "").strip()
    if configured_path:
        return Path(configured_path)

    hf_data_dir = Path("/data")
    if os.name != "nt" and (hf_data_dir.exists() or _running_on_hugging_face()):
        return hf_data_dir / "invite_codes.db"

    return Path(__file__).resolve().parent.parent / "data" / "invite_codes.db"


def _running_on_hugging_face() -> bool:
    return bool(
        os.getenv("SPACE_ID")
        or os.getenv("SPACE_HOST")
        or os.getenv("HF_SPACE_ID")
        or os.getenv("HF_SPACE_HOST")
    )


def _code_state_snapshot(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT code, max_uses, used_count, status, unlimited
        FROM invite_codes
        ORDER BY code
        """
    ).fetchall()
    return {
        row["code"]: {
            "used": int(row["used_count"]),
            "limit": None if bool(row["unlimited"]) else int(row["max_uses"]),
            "remaining": None
            if bool(row["unlimited"])
            else max(0, int(row["max_uses"]) - int(row["used_count"])),
            "status": row["status"],
            "unlimited": bool(row["unlimited"]),
            "valid": _quota_from_row(row)["valid"],
        }
        for row in rows
    }


def _quota_from_row(row: sqlite3.Row | None) -> dict[str, Any]:
    if not row:
        return _invalid_quota()

    unlimited = bool(row["unlimited"])
    limit = None if unlimited else max(1, int(row["max_uses"]))
    used = max(0, int(row["used_count"]))
    remaining = None if unlimited else max(0, int(limit) - used)
    valid = row["status"] == "active" and (unlimited or used < int(limit))
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
    raw_codes = _get_setting("INVITE_CODES", "")
    return _split_codes(raw_codes)


def _load_unlimited_invite_codes() -> list[str]:
    raw_codes = _get_setting("INVITE_UNLIMITED_CODES", "")
    return _split_codes(raw_codes)


def _split_codes(raw_codes: str) -> list[str]:
    codes = [
        code.strip()
        for code in raw_codes.replace("\n", ",").split(",")
        if code.strip()
    ]
    return sorted(set(codes))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
