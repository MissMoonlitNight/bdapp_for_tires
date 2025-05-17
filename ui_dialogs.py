# tire_app/ui_dialogs.py
import tkinter as tk
from tkinter import ttk, messagebox

class AddEditDialog(tk.Toplevel):
    """
    Класс для создания модального диалогового окна добавления/редактирования записи.
    """
    def __init__(self, parent, title, fields_config, db_manager, initial_values=None):
        """
        Конструктор диалога.

        :param parent: Родительское окно.
        :param title: Заголовок окна.
        :param fields_config: Словарь конфигурации полей диалога.
                               Ключ - отображаемое имя поля.
                               Значение - 'text' или словарь для dropdown.
                               Пример: {"ФИО": "text", "Клиент": {"type": "dropdown", "source": "clients"}}
        :param db_manager: Экземпляр DatabaseManager для получения данных для dropdown.
        :param initial_values: Словарь с начальными значениями для полей (при редактировании).
                               Ключи - отображаемые имена полей или специальные ключи для FK (idclient).
        """
        super().__init__(parent)
        self.transient(parent) # Диалог поверх родительского окна
        self.title(title)
        self.parent = parent
        self.result = None # Результат работы диалога (введенные данные)
        self.db_manager = db_manager # Для загрузки данных в выпадающие списки

        self.fields_config = fields_config
        self.initial_values = initial_values if initial_values else {}
        self.entries = {} # Словарь для хранения виджетов ввода (Entry, Combobox)

        self._create_widgets()
        self.grab_set() # Делает окно модальным (блокирует другие окна приложения)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Обработка закрытия окна крестиком
        self.wait_window(self) # Ожидание закрытия этого окна

    def _create_widgets(self):
        """
        Создает виджеты в диалоговом окне на основе fields_config.
        """
        form_frame = ttk.Frame(self, padding="10")
        form_frame.pack(expand=True, fill="both")

        row_num = 0
        for field_name, config in self.fields_config.items():
            ttk.Label(form_frame, text=f"{field_name}:").grid(row=row_num, column=0, sticky="w", pady=2, padx=5)

            field_type = config if isinstance(config, str) else config.get("type", "text")
            # Начальное значение для поля, ключ - отображаемое имя поля (field_name)
            initial_val = self.initial_values.get(field_name, "")

            if field_type == "dropdown":
                source_method_name = config.get("source") # Имя метода в db_manager для получения данных
                items_for_dropdown = {} # Словарь {отображаемое_значение: ID}

                # Загрузка данных для выпадающего списка
                if source_method_name == "clients":
                    data = self.db_manager.get_clients_for_dropdown()
                    if data: items_for_dropdown = {item['FIO']: item['idclient'] for item in data}
                    # Для установки начального значения dropdown при редактировании:
                    # initial_values может содержать 'idclient', а field_name - 'ФИО_Клиента'.
                    if field_name == "ФИО_Клиента" and "idclient" in self.initial_values:
                        client_id_to_select = self.initial_values.get("idclient")
                        for display_name, actual_id in items_for_dropdown.items():
                            if actual_id == client_id_to_select:
                                initial_val = display_name # Устанавливаем ФИО в Combobox
                                break
                elif source_method_name == "employees":
                    data = self.db_manager.get_employees_for_dropdown()
                    if data: items_for_dropdown = {item['FIO']: item['idemployee'] for item in data}
                    if field_name == "ФИО_Сотрудника" and "idemployee" in self.initial_values:
                        emp_id_to_select = self.initial_values.get("idemployee")
                        for display_name, actual_id in items_for_dropdown.items():
                            if actual_id == emp_id_to_select:
                                initial_val = display_name
                                break
                elif source_method_name == "products":
                    data = self.db_manager.get_products_for_dropdown()
                    if data: items_for_dropdown = {item['description']: item['idproduct'] for item in data}
                    # field_name здесь, например, "Продукт", а в initial_values ожидаем "idproduct"
                    if field_name == "Продукт" and "idproduct" in self.initial_values:
                        prod_id_to_select = self.initial_values.get("idproduct")
                        for display_name, actual_id in items_for_dropdown.items():
                            if actual_id == prod_id_to_select:
                                initial_val = display_name
                                break

                combo = ttk.Combobox(form_frame, state="readonly", width=30)
                combo['values'] = list(items_for_dropdown.keys())
                if initial_val and initial_val in combo['values']:
                    combo.set(initial_val)

                combo.grid(row=row_num, column=1, sticky="ew", pady=2, padx=5)
                self.entries[field_name] = {"widget": combo, "type": "dropdown", "map": items_for_dropdown}
            else: # По умолчанию текстовое поле ввода
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=row_num, column=1, sticky="ew", pady=2, padx=5)
                if initial_val is not None: # Устанавливаем начальное значение, если есть
                    entry.insert(0, str(initial_val))
                self.entries[field_name] = {"widget": entry, "type": "text"}
            row_num += 1

        form_frame.columnconfigure(1, weight=1) # Позволяет полю ввода растягиваться

        # Кнопки OK и Отмена
        button_frame = ttk.Frame(self, padding="5")
        button_frame.pack(fill="x", side="bottom") # Размещаем внизу
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Отмена", command=self._on_cancel).pack(side="right")

    def _on_ok(self):
        """
        Обработчик нажатия кнопки "OK".
        Собирает данные из полей ввода и сохраняет их в self.result.
        """
        self.result = {}
        try:
            for field_name, data in self.entries.items():
                widget = data["widget"]
                if data["type"] == "dropdown":
                    selected_display_val = widget.get()
                    if selected_display_val:
                        # Преобразуем отображаемое значение из Combobox обратно в ID,
                        # используя карту 'map', созданную при заполнении Combobox.
                        # Ключ для self.result должен быть именем столбца БД (например, 'idclient').
                        if field_name == "ФИО_Клиента":
                            self.result["idclient"] = data["map"][selected_display_val]
                        elif field_name == "ФИО_Сотрудника":
                            self.result["idemployee"] = data["map"][selected_display_val]
                        elif field_name == "Продукт": # Отображаемое имя "Продукт", сохраняем 'idproduct'
                            self.result["idproduct"] = data["map"][selected_display_val]
                        else: # Для других dropdown (если будут)
                             self.result[field_name] = data["map"][selected_display_val]
                    else:
                        # Если для обязательного выпадающего списка ничего не выбрано
                        if self.fields_config[field_name].get("required", False): # Допустим, есть ключ 'required'
                            messagebox.showwarning("Ошибка ввода", f"Пожалуйста, выберите значение для '{field_name}'.", parent=self)
                            self.result = None # Делаем результат невалидным
                            return
                        else: # Если не обязательно, можем пропустить или сохранить None/пустое значение
                            if field_name == "ФИО_Клиента": self.result["idclient"] = None
                            elif field_name == "ФИО_Сотрудника": self.result["idemployee"] = None
                            elif field_name == "Продукт": self.result["idproduct"] = None


                else: # Текстовое поле
                    self.result[field_name] = widget.get()

            # Простая валидация на пустоту (пример)
            for field_display_name, value in self.result.items():
                # Проверяем только те поля, которые не являются FK и ожидаются как текст
                is_fk_field = field_display_name in ["idclient", "idemployee", "idproduct"]
                # Проверяем оригинальную конфигурацию, а не result.keys()
                original_field_config = self.fields_config.get(field_display_name)

                if not is_fk_field and isinstance(original_field_config, str) and not value: # Если это текстовое поле и оно пустое
                    messagebox.showwarning("Ошибка ввода", f"Поле '{field_display_name}' не может быть пустым.", parent=self)
                    self.result = None
                    return
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обработки ввода: {e}", parent=self)
            self.result = None
            return

        if self.result is not None: # Если все хорошо
            self.destroy() # Закрываем диалог

    def _on_cancel(self):
        """
        Обработчик нажатия кнопки "Отмена" или закрытия окна.
        """
        self.result = None # Результат отсутствует
        self.destroy()