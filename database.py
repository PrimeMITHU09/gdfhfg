import sqlite3
from datetime import datetime
from config import DB_PATH, DEFAULT_PROXY


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Table for bot users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                selected_proxy TEXT DEFAULT 'H143Proxy',
                check_count INTEGER DEFAULT 0,
                last_checked_user TEXT,
                last_checked_at TEXT,
                last_active_at TEXT,
                created_at TEXT
            )
        """)

        # Table for check history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                proxy_username TEXT,
                mb_purchased REAL,
                mb_used REAL,
                mb_remaining REAL,
                checked_at TEXT
            )
        """)

        # Table for dynamic bot settings (e.g. custom welcome message)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Ensure last_active_at column exists if table was created earlier without it
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_active_at TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists

        conn.commit()


def register_or_update_user(user_id: int, username: str, first_name: str, last_name: str = "") -> bool:
    """
    Registers a new user or updates existing user.
    Returns True if this is a newly registered user, False otherwise.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    is_new = False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            is_new = True
            cursor.execute("""
                INSERT INTO users (user_id, first_name, last_name, username, selected_proxy, check_count, last_active_at, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """, (user_id, first_name, last_name or "", username or "", DEFAULT_PROXY, now_str, now_str))
        else:
            cursor.execute("""
                UPDATE users
                SET first_name = ?, last_name = ?, username = ?, last_active_at = ?
                WHERE user_id = ?
            """, (first_name, last_name or "", username or "", now_str, user_id))
        conn.commit()
    return is_new


def touch_user_activity(user_id: int):
    """Updates user last active timestamp."""
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_active_at = ? WHERE user_id = ?", (now_str, user_id))
        conn.commit()


def set_user_proxy(user_id: int, proxy_name: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET selected_proxy = ? WHERE user_id = ?", (proxy_name, user_id))
        conn.commit()


def record_check(user_id: int, proxy_username: str, mb_purchased: float, mb_used: float, mb_remaining: float):
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    with get_connection() as conn:
        cursor = conn.cursor()
        # Increment user check count and update last check & last active
        cursor.execute("""
            UPDATE users
            SET check_count = check_count + 1,
                last_checked_user = ?,
                last_checked_at = ?,
                last_active_at = ?
            WHERE user_id = ?
        """, (proxy_username, now_str, now_str, user_id))

        # Add history log
        cursor.execute("""
            INSERT INTO check_history (user_id, proxy_username, mb_purchased, mb_used, mb_remaining, checked_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, proxy_username, mb_purchased, mb_used, mb_remaining, now_str))
        conn.commit()


def get_user(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, first_name, last_name, username, selected_proxy, check_count,
                   last_checked_user, last_checked_at, last_active_at, created_at
            FROM users WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "username": row[3],
            "selected_proxy": row[4] or DEFAULT_PROXY,
            "check_count": row[5] or 0,
            "last_checked_user": row[6],
            "last_checked_at": row[7],
            "last_active_at": row[8] or row[9],
            "created_at": row[9],
        }


def get_user_history(user_id: int, limit: int = 5):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT proxy_username, mb_purchased, mb_used, mb_remaining, checked_at
            FROM check_history
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        return [
            {
                "proxy_username": r[0],
                "mb_purchased": r[1],
                "mb_used": r[2],
                "mb_remaining": r[3],
                "checked_at": r[4],
            }
            for r in rows
        ]


def get_all_users(limit: int = 50, offset: int = 0):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, first_name, last_name, username, check_count, last_active_at, created_at
            FROM users
            ORDER BY user_id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = cursor.fetchall()
        return [
            {
                "user_id": r[0],
                "first_name": r[1],
                "last_name": r[2],
                "username": r[3],
                "check_count": r[4] or 0,
                "last_active_at": r[5] or "N/A",
                "created_at": r[6] or "N/A",
            }
            for r in rows
        ]


def get_all_user_ids():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [r[0] for r in cursor.fetchall()]


def get_admin_stats():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(check_count) FROM users")
        total_checks = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM check_history")
        total_history_logs = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(mb_purchased) FROM check_history")
        total_mb_queried = cursor.fetchone()[0] or 0.0

        return {
            "total_users": total_users,
            "total_checks": total_checks or total_history_logs,
            "total_mb_queried": total_mb_queried
        }


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default


def set_setting(key: str, value: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        conn.commit()
