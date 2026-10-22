
import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "expenses.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Add user_id to an existing expenses table if necessary.
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
        }

        if "user_id" not in columns:
            conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")


def create_user(username: str, password_hash: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username.strip(), password_hash),
        )
        return cursor.lastrowid


def get_user_by_username(username: str):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()


def get_user_by_id(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def add_expense(title, amount, category, date, user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO expenses (title, amount, category, date, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (title, amount, category, str(date), user_id))
        return cursor.lastrowid


def get_expenses(user_id: int):
    with get_connection() as conn:
        return conn.execute("""
            SELECT id, title, amount, category, date
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
        """, (user_id,)).fetchall()


def delete_expense(expense_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        return cursor.rowcount > 0
