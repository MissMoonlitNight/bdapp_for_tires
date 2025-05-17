# tire_mvc_app/view/dialogs_view.py
import tkinter as tk
from tkinter import ttk, messagebox


class AddEditDialogView(tk.Toplevel):
    """
    Вид для диалогового окна добавления/редактирования записи.
    Не содержит логики работы с БД, только отображение и сбор данных.
    """

    def __init__(self, parent, title, fields_config, db_manager_for_fk, initial_values=None, current_table_name=None):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.result = None  # Результат работы диалога (введенные данные)
        self.db_manager_for_fk = db_manager_for_fk  # Для загрузки данных в выпадающие списки FK
        self.current_table_name = current_table_name  # Для специфичной логики (например, валидация цены шин)

        self.fields_config = fields_config
        self.initial_values = initial_values if initial_values else {}
        self.entries_widgets = {}  # Словарь для хранения виджетов ввода (Entry, Combobox)

        self._create_widgets()
        self.grab_set()  # Модальность
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        # self.wait_window(self) # wait_window должен вызываться из вызывающего кода (MainView)

    def _create_widgets(self):
        form_frame = ttk.Frame(self, padding="10")
        form_frame.pack(expand=True, fill="both")
        row_num = 0

        for field_name, config in self.fields_config.items():
            ttk.Label(form_frame, text=f"{field_name}:").grid(row=row_num, column=0, sticky="w", pady=2, padx=5)
            field_type = config if isinstance(config, str) else config.get("type", "text")
            initial_val = self.initial_values.get(field_name, "")

            if field_type == "dropdown" and self.db_manager_for_fk:  # Убедимся, что db_manager передан
                source_method_name = config.get("source")
                items_for_dropdown = {}
                # Загрузка данных для выпадающего списка через db_manager
                if source_method_name == "clients":
                    data = self.db_manager_for_fk.get_clients_for_dropdown()
                    if data: items_for_dropdown = {item['FIO']: item['idclient'] for item in data}
                    # Установка начального значения для dropdown при редактировании
                    if field_name == "ФИО_Клиента" and "idclient" in self.initial_values:
                        for display, actual_id in items_for_dropdown.items():
                            if actual_id == self.initial_values["idclient"]: initial_val = display; break
                elif source_method_name == "employees":
                    data = self.db_manager_for_fk.get_employees_for_dropdown()
                    if data: items_for_dropdown = {item['FIO']: item['idemployee'] for item in data}
                    if field_name == "ФИО_Сотрудника" and "idemployee" in self.initial_values:
                        for display, actual_id in items_for_dropdown.items():
                            if actual_id == self.initial_values["idemployee"]: initial_val = display; break

                combo = ttk.Combobox(form_frame, state="readonly", width=30)
                combo['values'] = list(items_for_dropdown.keys())
                if initial_val and initial_val in combo['values']: combo.set(initial_val)
                combo.grid(row=row_num, column=1, sticky="ew", pady=2, padx=5)
                self.entries_widgets[field_name] = {"widget": combo, "type": "dropdown", "map": items_for_dropdown}
            else:  # Текстовое поле
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=row_num, column=1, sticky="ew", pady=2, padx=5)
                if initial_val is not None: entry.insert(0, str(initial_val))
                self.entries_widgets[field_name] = {"widget": entry, "type": "text"}
            row_num += 1

        form_frame.columnconfigure(1, weight=1)
        button_frame = ttk.Frame(self, padding="5")
        button_frame.pack(fill="x", side="bottom")
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Отмена", command=self._on_cancel).pack(side="right")

    def _on_ok(self):
        self.result = {}
        try:
            for field_name, data in self.entries_widgets.items():
                widget = data["widget"]
                if data["type"] == "dropdown":
                    selected_display_val = widget.get()
                    if selected_display_val:
                        # Преобразование отображаемого значения в ID, ключ результата - имя столбца БД
                        if field_name == "ФИО_Клиента":
                            self.result["idclient"] = data["map"][selected_display_val]
                        elif field_name == "ФИО_Сотрудника":
                            self.result["idemployee"] = data["map"][selected_display_val]
                        else:
                            self.result[field_name] = data["map"][selected_display_val]  # Общий случай
                    # else: обработка, если dropdown обязателен, но не выбран
                else:  # Текстовое поле
                    value = widget.get()
                    if self.current_table_name == "tires" and field_name == "Цена_Продукта":
                        try:
                            price_val = float(value)
                            if price_val < 0: messagebox.showwarning("Ошибка", "Цена не м.б. < 0.",
                                                                     parent=self); self.result = None; return
                            self.result[field_name] = price_val  # Сохраняем как число
                        except ValueError:
                            messagebox.showwarning("Ошибка", "Цена должна быть числом.",
                                                   parent=self); self.result = None; return
                    else:
                        self.result[field_name] = value

            # Валидация на пустоту для других полей
            for field_display_name, value in self.result.items():
                if self.current_table_name == "tires" and field_display_name == "Цена_Продукта": continue
                original_config = self.fields_config.get(field_display_name)
                if isinstance(original_config, str) and not value:
                    messagebox.showwarning("Ошибка", f"Поле '{field_display_name}' не м.б. пустым.", parent=self);
                    self.result = None;
                    return
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка ввода: {e}", parent=self); self.result = None; return

        if self.result is not None:

            if self.current_table_name == "tires" and "idproduct" in self.initial_values:
                self.result["idproduct"] = self.initial_values["idproduct"]

            self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()