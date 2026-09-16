# controllers/undo_commands.py

from PyQt5.QtWidgets import QUndoCommand


class CellEditCommand(QUndoCommand):
    def __init__(self, controller, row, col, old_value, new_value,
                 description="Изменение ячейки"):
        super().__init__(description)
        self.controller = controller
        self.row = row
        self.col = col
        self.old_value = old_value
        self.new_value = new_value

    def _apply(self, value):
        """Записывает значение в модель и в ячейку таблицы."""
        # модель
        self.controller.set_cell_value(self.row, self.col, value)
        # ячейка — блокируем сигналы, чтобы не сработал on_cell_changed
        item = self.controller.table.item(self.row, self.col)
        if item is not None:
            self.controller.table.blockSignals(True)
            item.setText(value)
            self.controller.table.blockSignals(False)
        # валидация + автосохранение
        self.controller.on_model_changed()

    def redo(self):
        # Всегда применяем new_value сами.
        # Ветка «_first_redo» не нужна: push() вызовет redo(),
        # и мы сами синхронизируем и модель, и таблицу.
        self._apply(self.new_value)

    def undo(self):
        self._apply(self.old_value)