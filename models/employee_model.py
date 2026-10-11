# models/employee_model.py

import contextlib
import logging

from utils.database import get_connection


logger = logging.getLogger(__name__)


class EmployeeModel:
    @staticmethod
    def get_all():
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, category FROM employees ORDER BY name, id"
                )
                rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception:
            logger.exception("Ошибка чтения справочника сотрудников")
            raise

    @staticmethod
    def add(name, category):
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO employees (name, category) VALUES (?, ?)",
                    (name, category)
                )
                conn.commit()
                new_id = cursor.lastrowid
            return new_id
        except Exception:
            logger.exception("Ошибка добавления сотрудника в справочник")
            raise

    @staticmethod
    def update(emp_id, name, category):
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE employees SET name=?, category=? WHERE id=?",
                    (name, category, emp_id)
                )
                conn.commit()
        except Exception:
            logger.exception("Ошибка обновления сотрудника id=%s", emp_id)
            raise

    @staticmethod
    def delete(emp_id):
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
                conn.commit()
        except Exception:
            logger.exception("Ошибка удаления сотрудника id=%s", emp_id)
            raise

    @staticmethod
    def get_by_id(emp_id):
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, category FROM employees WHERE id=?",
                    (emp_id,)
                )
                row = cursor.fetchone()
            return dict(row) if row else None
        except Exception:
            logger.exception("Ошибка чтения сотрудника id=%s", emp_id)
            raise