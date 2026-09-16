# models/autosave_model.py

from utils.database import get_connection


class AutosaveModel:
    @staticmethod
    def save(json_str):
        """Сохраняет JSON-строку модели, заменяя все предыдущие записи."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM autosave")
        cursor.execute("INSERT INTO autosave (data_json) VALUES (?)", (json_str,))
        conn.commit()
        conn.close()

    @staticmethod
    def load_latest():
        """Возвращает последнюю сохранённую JSON-строку или None."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM autosave ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row["data_json"] if row else None

    @staticmethod
    def clear():
        """Удаляет все записи автосохранения."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM autosave")
        conn.commit()
        conn.close()