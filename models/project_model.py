# models/project_model.py

import json
import calendar
from utils.constants import MONTHS, PROJECT_VERSION
from app_config import ROLE

class ProjectModel:
    def __init__(self, month=0, year=2025):
        self.month = month          # 0-11
        self.year = year
        self.role = ROLE            # "doctor" или "nurse"
        self.employees = []         # список словарей {id, name, category, days: [...]}
        self.special = {
            "Э": [],   # эндоскопия
            "О": []    # операционная
        }
        self.notes = []             # примечания по дням (свободный текст)
        self.next_id = 1
        self._dirty = False

        self._init_special_rows()
        self._init_notes()

    def _init_special_rows(self):
        days = self.days_in_month()
        for key in self.special:
            self.special[key] = ["3"] * days

    def _init_notes(self):
        """Инициализирует массив примечаний пустыми строками."""
        days = self.days_in_month()
        self.notes = [""] * days

    def days_in_month(self):
        return calendar.monthrange(self.year, self.month + 1)[1]

    def add_employee(self, name, category):
        emp_id = self.next_id
        self.next_id += 1
        count = self.days_in_month()
        days = [""] * count
        duty_home = [False] * count
        employee = {
            "id": emp_id,
            "name": name,
            "category": category,
            "days": days,
            "duty_home": duty_home,
        }
        self.employees.append(employee)
        self._dirty = True
        return emp_id

    def remove_employee(self, emp_id):
        self.employees = [e for e in self.employees if e["id"] != emp_id]
        self._dirty = True

    def get_employee(self, emp_id):
        for emp in self.employees:
            if emp["id"] == emp_id:
                return emp
        return None

    def set_day(self, emp_id, day_index, value):
        emp = self.get_employee(emp_id)
        if emp and 0 <= day_index < len(emp["days"]):
            emp["days"][day_index] = value
            self._dirty = True

    def set_duty_home(self, emp_id, day_index, value):
        """Устанавливает или снимает флаг дежурства на дому."""
        emp = self.get_employee(emp_id)
        if emp and 0 <= day_index < len(emp["duty_home"]):
            emp["duty_home"][day_index] = bool(value)
            self._dirty = True

    def get_duty_home(self, emp_id, day_index):
        """Возвращает True, если сотрудник дежурит на дому в этот день."""
        emp = self.get_employee(emp_id)
        if emp and 0 <= day_index < len(emp["duty_home"]):
            return emp["duty_home"][day_index]
        return False

    def set_special(self, row_key, day_index, value):
        if row_key in self.special and 0 <= day_index < len(self.special[row_key]):
            self.special[row_key][day_index] = value
            self._dirty = True

    def set_note(self, day_index, value):
        """Записывает примечание для указанного дня (0-based)."""
        if 0 <= day_index < len(self.notes):
            self.notes[day_index] = value
            self._dirty = True        

    def to_json(self):
        data = {
            "version": PROJECT_VERSION,
            "role": self.role,
            "month": self.month,
            "year": self.year,
            "employees": self.employees,
            "special": self.special,
            "notes": self.notes,
            "nextId": self.next_id
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def from_json(self, json_str):
        data = json.loads(json_str)
        if data.get("version") != PROJECT_VERSION:
            print("Внимание: версия проекта отличается от текущей")
        # Роль: старые файлы (v1.0) не имеют поля — считаем их врачебными
        self.role = data.get("role", "doctor")
        self.month = data["month"]
        self.year = data["year"]
        self.employees = data["employees"]
        self.special = data["special"]
        self.next_id = data["nextId"]
        # Примечания: в версии 2.0 поля не было — подставляем пустые
        if "notes" in data and isinstance(data["notes"], list):
            self.notes = data["notes"]
        else:
            self.notes = [""] * self.days_in_month()
        # duty_home: в версиях 2.0–2.1 поля не было — инициализируем False
        count = self.days_in_month()
        for emp in self.employees:
            if "duty_home" not in emp or not isinstance(emp["duty_home"], list):
                emp["duty_home"] = [False] * count
            elif len(emp["duty_home"]) != count:
                emp["duty_home"] = (emp["duty_home"] + [False] * count)[:count]
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def mark_clean(self):
        self._dirty = False

    def get_employee_count(self):
        return len(self.employees)