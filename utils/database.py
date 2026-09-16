# utils/database.py

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "app_data.db")


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
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='employees'")
    row = cursor.fetchone()
    if not row:
        return
    sql = (row[0] or "").upper()
    if "UNIQUE" not in sql:
        return

    # Миграция: сохранить данные, пересоздать таблицу без UNIQUE
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