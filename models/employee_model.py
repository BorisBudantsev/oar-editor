# models/employee_model.py

import contextlib
from utils.database import get_connection


class EmployeeModel:
    @staticmethod
    def get_all():
        with contextlib.closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, category FROM employees ORDER BY name, id"
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def add(name, category):
        with contextlib.closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO employees (name, category) VALUES (?, ?)",
                (name, category)
            )
            conn.commit()
            new_id = cursor.lastrowid
        return new_id

    @staticmethod
    def update(emp_id, name, category):
        with contextlib.closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE employees SET name=?, category=? WHERE id=?",
                (name, category, emp_id)
            )
            conn.commit()

    @staticmethod
    def delete(emp_id):
        with contextlib.closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            conn.commit()

    @staticmethod
    def get_by_id(emp_id):
        with contextlib.closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, category FROM employees WHERE id=?",
                (emp_id,)
            )
            row = cursor.fetchone()
        return dict(row) if row else None