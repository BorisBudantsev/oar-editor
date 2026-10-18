# models/autosave_model.py

import contextlib
import logging

from utils.database import get_connection


logger = logging.getLogger(__name__)


class AutosaveModel:
    @staticmethod
    def save(json_str):
        """Сохраняет JSON-строку модели, заменяя все предыдущие записи.

        Порядок операций намеренный: сначала INSERT новой записи, затем
        удаление старых. Если запись новой версии не удалась, предыдущая
        (единственная пригодная) копия несохранённых данных остаётся целой.

        Важно: json_str содержит персональные данные (ФИО), поэтому
        в лог она НЕ пишется.
        """
        try:
            with contextlib.closing(get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO autosave (data_json) VALUES (?)", (json_str,)
                )
                new_id = cursor.lastrowid
                cursor.execute(
                    "DELETE FROM autosave WHERE id <> ?", (new_id,)
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