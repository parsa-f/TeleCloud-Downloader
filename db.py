"""
db.py - PostgreSQL-backed User Management for TeleCloud-Downloader.

Replaces the old SQLite file (/app/user_configs/telecloud.db) with a managed
Postgres instance (Railway plugin) to avoid filling the small container disk.
Each user can store their own GitHub token (github_token) for per-user uploads.
"""

import re
import os
import threading
from datetime import date, datetime, timedelta, timezone

# Read DATABASE_URL directly from env to avoid circular import with config.py
DATABASE_URL = os.environ.get("DATABASE_URL", "")

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3

_local = threading.local()
_db_lock = threading.Lock()


def _get_conn():
    """Thread-local connection (psycopg2 connections are not thread-safe)."""
    conn = getattr(_local, "conn", None)
    is_closed = False
    if conn is not None:
        # psycopg2 has .closed; sqlite3 does not
        is_closed = getattr(conn, "closed", 0) != 0 if USE_POSTGRES else False
        if not USE_POSTGRES and conn is not None:
            # sqlite3: check via in-transition state
            try:
                conn.execute("SELECT 1")
            except Exception:
                is_closed = True
    if conn is None or is_closed:
        if USE_POSTGRES:
            _local.conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            _local.conn.autocommit = False
        else:
            _local.conn = sqlite3.connect("/app/user_configs/telecloud.db", check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
            _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


def _sql(q: str) -> str:
    """Convert sqlite-style '?' placeholders to psycopg2 '%s' (no-op for sqlite)."""
    return q.replace("?", "%s") if USE_POSTGRES else q


def _run(q: str, params: tuple = ()):
    with _db_lock:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(_sql(q), params)
        conn.commit()
        return cur


def _fetchone(q: str, params: tuple = ()):
    with _db_lock:
        conn = _get_conn()
        if USE_POSTGRES:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = conn.cursor()
        cur.execute(_sql(q), params)
        return cur.fetchone()


def _fetchall(q: str, params: tuple = ()):
    with _db_lock:
        conn = _get_conn()
        if USE_POSTGRES:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = conn.cursor()
        cur.execute(_sql(q), params)
        return cur.fetchall()


def _ensure_users_columns(conn) -> None:
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
        cols = {r[0] for r in cur.fetchall()}
        adds = [
            "username TEXT",
            "display_name TEXT",
            "monthly_files_downloaded INTEGER NOT NULL DEFAULT 0",
            "monthly_bytes_downloaded INTEGER NOT NULL DEFAULT 0",
            "last_active_month TEXT",
            "custom_quota_monthly_files INTEGER",
            "custom_quota_monthly_bytes INTEGER",
            "github_token TEXT",
            "github_repo TEXT",
            "upload_dest TEXT NOT NULL DEFAULT 'tg'",
        ]
        for col in adds:
            name = col.split()[0]
            if name not in cols:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col}")
        conn.commit()
    else:
        # SQLite: check pragma, add missing columns
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {r[1] for r in cur.fetchall()}
        adds = [
            "username TEXT",
            "display_name TEXT",
            "monthly_files_downloaded INTEGER NOT NULL DEFAULT 0",
            "monthly_bytes_downloaded INTEGER NOT NULL DEFAULT 0",
            "last_active_month TEXT",
            "custom_quota_monthly_files INTEGER",
            "custom_quota_monthly_bytes INTEGER",
            "github_token TEXT",
            "github_repo TEXT",
            "upload_dest TEXT NOT NULL DEFAULT 'tg'",
        ]
        for col in adds:
            name = col.split()[0]
            if name not in cols:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col}")
        conn.commit()


def init_db() -> None:
    with _db_lock:
        conn = _get_conn()
        if USE_POSTGRES:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id            BIGINT PRIMARY KEY,
                    is_approved        INTEGER NOT NULL DEFAULT 0,
                    files_downloaded   INTEGER NOT NULL DEFAULT 0,
                    bytes_downloaded   BIGINT NOT NULL DEFAULT 0,
                    last_active_date   TEXT,
                    custom_quota_files INTEGER,
                    custom_quota_bytes BIGINT,
                    default_quality    TEXT    NOT NULL DEFAULT '720',
                    audio_mode         INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()
            _ensure_users_columns(conn)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS download_events (
                    id               SERIAL PRIMARY KEY,
                    user_id          BIGINT NOT NULL,
                    bytes_downloaded BIGINT NOT NULL,
                    created_at       TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_download_events_user_created "
                "ON download_events(user_id, created_at)"
            )
            conn.commit()
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    is_approved        INTEGER NOT NULL DEFAULT 0,
                    files_downloaded   INTEGER NOT NULL DEFAULT 0,
                    bytes_downloaded   INTEGER NOT NULL DEFAULT 0,
                    last_active_date   TEXT,
                    custom_quota_files INTEGER,
                    custom_quota_bytes INTEGER,
                    default_quality    TEXT    NOT NULL DEFAULT '720',
                    audio_mode         INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS download_events (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id          INTEGER NOT NULL,
                    bytes_downloaded INTEGER NOT NULL,
                    created_at       TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_download_events_user_created "
                "ON download_events(user_id, created_at)"
            )
            conn.commit()
            _ensure_users_columns(conn)


def _normalize_username(username):
    if not username:
        return None
    value = username.strip().lstrip("@").lower()
    return value or None


def _normalize_display_name(display_name):
    if not display_name:
        return None
    value = re.sub(r"\s+", " ", display_name).strip()
    return value or None


def _now_utc_sql() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------

def add_user(user_id: int, approved: bool = False) -> None:
    _run(
        "INSERT INTO users (user_id, is_approved) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO NOTHING",
        (user_id, int(approved)),
    )


def touch_user_identity(user_id: int, username, display_name) -> None:
    uname = _normalize_username(username)
    dname = _normalize_display_name(display_name)
    _run(
        "INSERT INTO users (user_id, username, display_name) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "username=COALESCE(excluded.username, users.username), "
        "display_name=COALESCE(excluded.display_name, users.display_name)",
        (user_id, uname, dname),
    )


def approve_user(user_id: int) -> None:
    _run(
        "INSERT INTO users (user_id, is_approved) VALUES (?, 1) "
        "ON CONFLICT(user_id) DO UPDATE SET is_approved=1",
        (user_id,),
    )


def reject_user(user_id: int) -> None:
    _run(
        "INSERT INTO users (user_id, is_approved) VALUES (?, 0) "
        "ON CONFLICT(user_id) DO UPDATE SET is_approved=0",
        (user_id,),
    )


def set_user_approved(user_id: int, approved: bool) -> None:
    if approved:
        approve_user(user_id)
    else:
        reject_user(user_id)


def delete_user(user_id: int) -> None:
    from config import USER_CONFIGS_DIR
    import os
    _run("DELETE FROM users WHERE user_id=?", (user_id,))


def get_user(user_id: int):
    return _fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))


def is_approved(user_id: int) -> bool:
    row = get_user(user_id)
    return bool(row and row["is_approved"])


def get_all_approved_users() -> list:
    rows = _fetchall("SELECT user_id FROM users WHERE is_approved=1")
    return [r["user_id"] for r in rows]


def _user_search_where(query):
    if not query:
        return "1=1", []
    q = query.strip()
    if not q:
        return "1=1", []
    if q.isdigit():
        return "user_id = ?", [int(q)]
    q = q.lstrip("@").lower()
    like = f"%{q}%"
    return (
        "(LOWER(COALESCE(username,'')) LIKE ? OR LOWER(COALESCE(display_name,'')) LIKE ?)",
        [like, like],
    )


def count_all_signed_users(query=None) -> int:
    where_sql, params = _user_search_where(query)
    row = _fetchone(f"SELECT COUNT(*) AS c FROM users WHERE {where_sql}", params)
    return int(row["c"] if row else 0)


def list_all_signed_users(page: int, per_page: int, query=None):
    page = max(page, 1)
    per_page = max(1, min(per_page, 50))
    offset = (page - 1) * per_page
    where_sql, params = _user_search_where(query)
    from config import ADMIN_ID
    return _fetchall(
        f"""
        SELECT
            user_id, is_approved,
            files_downloaded, bytes_downloaded, last_active_date,
            custom_quota_files, custom_quota_bytes,
            username, display_name
        FROM users
        WHERE {where_sql}
        ORDER BY
            CASE WHEN user_id = ? THEN 0 ELSE 1 END,
            user_id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, ADMIN_ID, per_page, offset],
    )


# ---------------------------------------------------------------------
# GitHub token (per-user)
# ---------------------------------------------------------------------

def set_github_token(user_id: int, token: str) -> None:
    _run(
        "INSERT INTO users (user_id, github_token) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET github_token=excluded.github_token",
        (user_id, token.strip()),
    )


def get_github_token(user_id: int):
    row = get_user(user_id)
    return row["github_token"] if row else None


def set_github_repo(user_id: int, repo: str) -> None:
    _run(
        "INSERT INTO users (user_id, github_repo) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET github_repo=excluded.github_repo",
        (user_id, repo.strip()),
    )


def set_upload_dest(user_id: int, dest: str) -> None:
    if dest not in ("tg", "s3", "github", "gd"):
        dest = "tg"
    _run(
        "INSERT INTO users (user_id, upload_dest) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET upload_dest=excluded.upload_dest",
        (user_id, dest),
    )


def get_upload_dest(user_id: int) -> str:
    row = get_user(user_id)
    if not row:
        return "tg"
    return row["upload_dest"] or "tg"


def get_github_repo(user_id: int):
    row = get_user(user_id)
    return row["github_repo"] if row else None


# ---------------------------------------------------------------------
# Quota helpers
# ---------------------------------------------------------------------

def set_custom_quota(user_id: int, files, bytes_) -> None:
    _run(
        "INSERT INTO users (user_id, custom_quota_files, custom_quota_bytes) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET custom_quota_files=excluded.custom_quota_files, "
        "custom_quota_bytes=excluded.custom_quota_bytes",
        (user_id, files, bytes_),
    )


def set_custom_quota_monthly(user_id: int, files, bytes_) -> None:
    _run(
        "INSERT INTO users (user_id, custom_quota_monthly_files, custom_quota_monthly_bytes) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET custom_quota_monthly_files=excluded.custom_quota_monthly_files, "
        "custom_quota_monthly_bytes=excluded.custom_quota_monthly_bytes",
        (user_id, files, bytes_),
    )


def get_effective_quota_bytes(user_id: int) -> int:
    from config import MAX_DAILY_BYTES
    row = get_user(user_id)
    if not row:
        return int(MAX_DAILY_BYTES)
    return int(row["custom_quota_bytes"]) if row["custom_quota_bytes"] is not None else int(MAX_DAILY_BYTES)


def get_effective_monthly_quota_bytes(user_id: int) -> int:
    from config import MAX_MONTHLY_BYTES
    row = get_user(user_id)
    if not row:
        return int(MAX_MONTHLY_BYTES)
    return int(row["custom_quota_monthly_bytes"]) if row["custom_quota_monthly_bytes"] is not None else int(MAX_MONTHLY_BYTES)


def get_effective_monthly_quota_files(user_id: int) -> int:
    from config import MAX_MONTHLY_FILES
    row = get_user(user_id)
    if not row:
        return int(MAX_MONTHLY_FILES)
    return int(row["custom_quota_monthly_files"]) if row["custom_quota_monthly_files"] is not None else int(MAX_MONTHLY_FILES)


def adjust_user_monthly_quota_bytes(user_id: int, delta_bytes: int) -> int:
    from config import MAX_MONTHLY_BYTES
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING", (user_id,))
    cur.execute("SELECT custom_quota_monthly_bytes FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    base = int(row[0]) if row and row[0] is not None else int(MAX_MONTHLY_BYTES)
    new_bytes = max(0, base + int(delta_bytes))
    cur.execute("UPDATE users SET custom_quota_monthly_bytes=? WHERE user_id=?", (new_bytes, user_id))
    conn.commit()
    return new_bytes


def adjust_user_usage_count(user_id: int, delta: int) -> int:
    conn = _get_conn()
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute("INSERT INTO users (user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING", (user_id,))
    cur.execute(
        "UPDATE users SET files_downloaded=MAX(files_downloaded + ?, 0), last_active_date=? WHERE user_id=?",
        (int(delta), today, user_id),
    )
    conn.commit()
    cur.execute("SELECT files_downloaded FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return int(row[0] if row else 0)


def adjust_user_quota_bytes(user_id: int, delta_bytes: int) -> int:
    from config import MAX_DAILY_BYTES
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING", (user_id,))
    cur.execute("SELECT custom_quota_bytes FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    base = int(row[0]) if row and row[0] is not None else int(MAX_DAILY_BYTES)
    new_bytes = max(0, base + int(delta_bytes))
    cur.execute("UPDATE users SET custom_quota_bytes=? WHERE user_id=?", (new_bytes, user_id))
    conn.commit()
    return new_bytes


# ---------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------

def update_setting(user_id: int, key: str, value) -> None:
    allowed = {"default_quality", "audio_mode"}
    if key not in allowed:
        raise ValueError(f"update_setting: unknown key '{key}'")
    _run(
        f"INSERT INTO users (user_id, {key}) VALUES (?, ?) "
        f"ON CONFLICT(user_id) DO UPDATE SET {key}=excluded.{key}",
        (user_id, value),
    )


# ---------------------------------------------------------------------
# Quota gate
# ---------------------------------------------------------------------

def check_and_update_quota(user_id: int, file_size_bytes: int) -> tuple:
    from config import (MAX_DAILY_FILES, MAX_DAILY_BYTES, MAX_MONTHLY_FILES, MAX_MONTHLY_BYTES)
    from locales import t
    from utils import fmt_size

    today_str = date.today().isoformat()
    month_str = date.today().strftime("%Y-%m")
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    row = get_user(user_id)
    if row is None:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = get_user(user_id)

    last_date = row["last_active_date"] or ""
    if last_date != today_str:
        cur.execute(
            "UPDATE users SET files_downloaded=0, bytes_downloaded=0, last_active_date=? WHERE user_id=?",
            (today_str, user_id),
        )
        conn.commit()
        row = get_user(user_id)

    last_month = row["last_active_month"] or ""
    if last_month != month_str:
        cur.execute(
            "UPDATE users SET monthly_files_downloaded=0, monthly_bytes_downloaded=0, last_active_month=? WHERE user_id=?",
            (month_str, user_id),
        )
        conn.commit()
        row = get_user(user_id)

    max_files = row["custom_quota_files"] if row["custom_quota_files"] is not None else MAX_DAILY_FILES
    max_bytes = row["custom_quota_bytes"] if row["custom_quota_bytes"] is not None else MAX_DAILY_BYTES

    files_used = row["files_downloaded"]
    bytes_used = row["bytes_downloaded"]

    if files_used >= max_files:
        return False, t(user_id, 'quota_files_exceeded', used=files_used, max=max_files)

    if bytes_used + file_size_bytes > max_bytes:
        return False, t(user_id, 'quota_bytes_exceeded', used=fmt_size(bytes_used), max=fmt_size(max_bytes))

    max_monthly_files = row["custom_quota_monthly_files"] if row["custom_quota_monthly_files"] is not None else MAX_MONTHLY_FILES
    max_monthly_bytes = row["custom_quota_monthly_bytes"] if row["custom_quota_monthly_bytes"] is not None else MAX_MONTHLY_BYTES

    monthly_files_used = row["monthly_files_downloaded"]
    monthly_bytes_used = row["monthly_bytes_downloaded"]

    if monthly_files_used >= max_monthly_files:
        return False, t(user_id, 'quota_monthly_files_exceeded', used=monthly_files_used, max=max_monthly_files)

    if monthly_bytes_used + file_size_bytes > max_monthly_bytes:
        return False, t(user_id, 'quota_monthly_bytes_exceeded', used=fmt_size(monthly_bytes_used), max=fmt_size(max_monthly_bytes))

    cur.execute(
        "UPDATE users SET files_downloaded=files_downloaded+1, "
        "bytes_downloaded=bytes_downloaded+?, last_active_date=?, "
        "monthly_files_downloaded=monthly_files_downloaded+1, "
        "monthly_bytes_downloaded=monthly_bytes_downloaded+?, last_active_month=? "
        "WHERE user_id=?",
        (file_size_bytes, today_str, file_size_bytes, month_str, user_id),
    )
    conn.commit()
    return True, ""


# ---------------------------------------------------------------------
# Download accounting
# ---------------------------------------------------------------------

def record_download_event(user_id: int, file_size_bytes: int, created_at: str = None) -> None:
    if file_size_bytes <= 0:
        return
    _run(
        "INSERT INTO download_events (user_id, bytes_downloaded, created_at) VALUES (?, ?, ?)",
        (user_id, int(file_size_bytes), created_at or _now_utc_sql()),
    )


def record_download_bytes(user_id: int, file_size_bytes: int) -> None:
    if file_size_bytes <= 0:
        return
    conn = _get_conn()
    cur = conn.cursor()
    # Upsert so stats also work for users absent from the table (e.g. admin).
    cur.execute(
        "INSERT INTO users (user_id, bytes_downloaded, monthly_bytes_downloaded, files_downloaded) "
        "VALUES (?, ?, ?, 1) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "bytes_downloaded=users.bytes_downloaded+excluded.bytes_downloaded, "
        "monthly_bytes_downloaded=users.monthly_bytes_downloaded+excluded.monthly_bytes_downloaded, "
        "files_downloaded=users.files_downloaded+1",
        (user_id, file_size_bytes, file_size_bytes),
    )
    conn.commit()
    record_download_event(user_id, file_size_bytes)


def get_user_download_stats(user_id: int) -> dict:
    now_local = datetime.now().astimezone()
    day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start_local = day_start_local - timedelta(days=day_start_local.weekday())
    month_start_local = day_start_local.replace(day=1)

    def to_utc_sql(dt_local):
        return dt_local.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

    day_start_utc = to_utc_sql(day_start_local)
    week_start_utc = to_utc_sql(week_start_local)
    month_start_utc = to_utc_sql(month_start_local)

    row = _fetchone(
        """
        SELECT
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS files_today,
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS files_week,
            SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END) AS files_month,
            COUNT(*)                                         AS files_all,
            COALESCE(SUM(CASE WHEN created_at >= ? THEN bytes_downloaded ELSE 0 END), 0) AS bytes_today,
            COALESCE(SUM(CASE WHEN created_at >= ? THEN bytes_downloaded ELSE 0 END), 0) AS bytes_week,
            COALESCE(SUM(CASE WHEN created_at >= ? THEN bytes_downloaded ELSE 0 END), 0) AS bytes_month,
            COALESCE(SUM(bytes_downloaded), 0)                                          AS bytes_all
        FROM download_events
        WHERE user_id=?
        """,
        (day_start_utc, week_start_utc, month_start_utc, day_start_utc, week_start_utc, month_start_utc, user_id),
    )

    if row is None:
        return {k: 0 for k in ["files_today", "files_week", "files_month", "files_all", "bytes_today", "bytes_week", "bytes_month", "bytes_all"]}
    return {k: int(row[k] or 0) for k in ["files_today", "files_week", "files_month", "files_all", "bytes_today", "bytes_week", "bytes_month", "bytes_all"]}


# ---------------------------------------------------------------------
# Global stats
# ---------------------------------------------------------------------

def get_global_stats() -> dict:
    row = _fetchone(
        """
        SELECT
            COUNT(CASE WHEN is_approved = 1 THEN 1 END) AS total_approved,
            COALESCE(SUM(files_downloaded), 0)           AS total_files,
            COALESCE(SUM(bytes_downloaded), 0)           AS total_bytes
        FROM users
        """
    )
    if row is None:
        return {"total_approved": 0, "total_files": 0, "total_bytes": 0}
    return {
        "total_approved": row["total_approved"],
        "total_files": row["total_files"],
        "total_bytes": row["total_bytes"],
    }
