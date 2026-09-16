# models/project_model.py

import json
import calendar
from utils.constants import MONTHS, PROJECT_VERSION

class ProjectModel:
    def __init__(self, month=0, year=2025):
        self.month = month          # 0-11
        self.year = year
        self.employees = []         # список словарей {id, name, category, days: [...]}
        self.special = {
            "Э": [],   # эндоскопия
            "О": []    # операционная
        }
        self.next_id = 1
        self._dirty = False

        self._init_special_rows()

    def _init_special_rows(self):
        days = self.days_in_month()
        for key in self.special:
            self.special[key] = ["3"] * days

    def days_in_month(self):
        return calendar.monthrange(self.year, self.month + 1)[1]

    def add_employee(self, name, category):
        emp_id = self.next_id
        self.next_id += 1
        days = [""] * self.days_in_month()
        employee = {
            "id": emp_id,
            "name": name,
            "category": category,
            "days": days
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

    def set_special(self, row_key, day_index, value):
        if row_key in self.special and 0 <= day_index < len(self.special[row_key]):
            self.special[row_key][day_index] = value
            self._dirty = True

    def to_json(self):
        data = {
            "version": PROJECT_VERSION,
            "month": self.month,
            "year": self.year,
            "employees": self.employees,
            "special": self.special,
            "nextId": self.next_id
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def from_json(self, json_str):
        data = json.loads(json_str)
        if data.get("version") != PROJECT_VERSION:
            print("Внимание: версия проекта отличается от текущей")
        self.month = data["month"]
        self.year = data["year"]
        self.employees = data["employees"]
        self.special = data["special"]
        self.next_id = data["nextId"]
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def mark_clean(self):
        self._dirty = False

    def get_employee_count(self):
        return len(self.employees)