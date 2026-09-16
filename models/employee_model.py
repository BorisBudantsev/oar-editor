# models/employee_model.py

import sqlite3
from utils.database import get_connection


class EmployeeModel:
    @staticmethod
    def get_all():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category FROM employees ORDER BY name, id")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def add(name, category):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO employees (name, category) VALUES (?, ?)",
                (name, category)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update(emp_id, name, category):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE employees SET name=?, category=? WHERE id=?",
            (name, category, emp_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def delete(emp_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_by_id(emp_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, category FROM employees WHERE id=?",
            (emp_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None