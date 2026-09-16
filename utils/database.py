# utils/database.py

import sqlite3
import os
import sys


def _get_db_path():
    """Определяет, куда писать app_data.db.

    - Собранный .exe (frozen) → %APPDATA%\\OAR_Editor\\app_data.db
    - Из исходников          → <проект>/data/app_data.db
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        app_dir = os.path.join(base, "OAR_Editor")
    else:
        app_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data"
        )
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "app_data.db")


DB_PATH = _get_db_path()


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    _migrate_employees_unique(conn)
    return conn


def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS autosave (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_json TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _migrate_employees_unique(conn):
    """Если в старой схеме было UNIQUE(name) — пересоздаём таблицу без него."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='employees'"
    )
    row = cursor.fetchone()
    if not row:
        return
    sql = (row[0] or "").upper()
    if "UNIQUE" not in sql:
        return

    cursor.execute("ALTER TABLE employees RENAME TO employees_old")
    cursor.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    cursor.execute("""
        INSERT INTO employees (id, name, category)
        SELECT id, name, category FROM employees_old
    """)
    cursor.execute("DROP TABLE employees_old")
    conn.commit()