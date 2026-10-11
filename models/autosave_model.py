# models/autosave_model.py

import contextlib
import logging

from utils.database import get_connection


logger = logging.getLogger(__name__)


class AutosaveModel:
    @staticmethod
    def save(json_str):
        """Сохраняет JSON-строку модели, заменяя все предыдущие записи.

        Важно: json_str содержит персональные данные (ФИО), поэтому
        в лог она НЕ пишется.
        """
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM autosave")
                cursor.execute(
                    "INSERT INTO autosave (data_json) VALUES (?)", (json_str,)
                )
                conn.commit()
        except Exception:
            logger.exception("Ошибка автосохранения")
            raise

    @staticmethod
    def load_latest():
        """Возвращает последнюю сохранённую JSON-строку или None."""
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data_json FROM autosave ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
            return row["data_json"] if row else None
        except Exception:
            logger.exception("Ошибка чтения автосохранения")
            raise

    @staticmethod
    def clear():
        """Удаляет все записи автосохранения."""
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM autosave")
                conn.commit()
        except Exception:
            logger.exception("Ошибка очистки автосохранения")
            raise