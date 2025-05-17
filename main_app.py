# tire_app/main_app.py
import tkinter as tk
from tkinter import ttk, messagebox
from database_manager import DatabaseManager
from ui_dialogs import AddEditDialog


class MainApp(tk.Tk):
    """
    Основной класс приложения с графическим интерфейсом.
    """

    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager  # Экземпляр для работы с БД
        self.title("Управление БД TireBD")
        self.geometry("1000x700")  # Увеличим размер для лучшего отображения

        self.current_table_name = tk.StringVar()  # Переменная для хранения имени текущей таблицы
        self.search_term = tk.StringVar()  # Переменная для строки поиска

        # Конфигурации для каждой таблицы
        # pk_column: Имя столбца первичного ключа в Treeview (обычно 'ID' после JOIN).
        # editable_fields: Словарь для диалога AddEditDialog.
        #    Ключ - отображаемое имя поля в диалоге.
        #    Значение - 'text' или словарь для dropdown.
        # initial_value_keys: Сопоставление имен столбцов из Treeview (или скрытых данных)
        #    с ключами, ожидаемыми AddEditDialog в initial_values.
        #    Ключ - имя поля в диалоге, значение - ключ в словаре данных строки Treeview.
        self.table_configs = {
            "client": {
                "pk_column_display": "ID",  # Как PK отображается в Treeview
                "editable_fields": {"FIO": "text", "Адрес": "text", "Телефон": "text"},
                "initial_value_keys": {"FIO": "FIO", "Адрес": "Адрес", "Телефон": "Телефон"}
            },
            "tires": {
                "pk_column_display": "ID",
                "editable_fields": {
                    "Тип": "text", "Сезон": "text", "Модель": "text",
                    "Продукт": {"type": "dropdown", "source": "products"}
                    # Отображается как "Продукт", ожидаем idproduct
                },
                # 'Продукт' в диалоге ожидает idproduct для pre-selection.
                # 'idproduct' - это ключ в данных строки, полученных из get_table_data для 'tires'.
                "initial_value_keys": {"Тип": "Тип", "Сезон": "Сезон", "Модель": "Модель", "Продукт": "idproduct"}
            },
            "order": {
                "pk_column_display": "ID",
                "editable_fields": {
                    "Дата": "text", "Статус": "text",
                    "ФИО_Клиента": {"type": "dropdown", "source": "clients"},
                    "ФИО_Сотрудника": {"type": "dropdown", "source": "employees"}
                },
                # 'ФИО_Клиента' в диалоге ожидает idclient, и т.д.
                "initial_value_keys": {"Дата": "Дата", "Статус": "Статус", "ФИО_Клиента": "idclient",
                                       "ФИО_Сотрудника": "idemployee"}
            }
        }
        # Столбцы, которые нужно скрыть в Treeview, но использовать для передачи в диалог редактирования (например, FK ID)
        self.hidden_columns_map = {
            "tires": ["idproduct"],
            "order": ["idclient", "idemployee"]
        }

        self._create_widgets()  # Создаем виджеты интерфейса
        self._load_table_names()  # Загружаем имена таблиц в выпадающий список

        # Устанавливаем начальную таблицу, если список не пуст
        if self.table_combobox['values']:
            self.table_combobox.current(0)  # Выбираем первый элемент
            # current_table_name обновится автоматически через textvariable
            self._on_table_select_event()  # Вызываем обработчик выбора таблицы

    def _create_widgets(self):
        """Создает все виджеты главного окна."""
        # Верхняя панель для элементов управления
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(fill="x")

        ttk.Label(control_frame, text="Выберите таблицу:").pack(side="left", padx=(0, 5))
        self.table_combobox = ttk.Combobox(control_frame, textvariable=self.current_table_name, state="readonly",
                                           width=20)
        self.table_combobox.pack(side="left", padx=(0, 10))
        self.table_combobox.bind("<<ComboboxSelected>>", self._on_table_select_event)  # Событие выбора из списка

        ttk.Label(control_frame, text="Поиск:").pack(side="left", padx=(10, 5))
        search_entry = ttk.Entry(control_frame, textvariable=self.search_term, width=30)
        search_entry.pack(side="left", padx=(0, 10))
        search_entry.bind("<KeyRelease>", self._on_search_change)  # Событие при отпускании клавиши

        # Панель для кнопок (справа)
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side="right")

        self.add_button = ttk.Button(button_frame, text="Добавить", command=self._on_add, state="disabled")
        self.add_button.pack(side="left", padx=5)
        self.edit_button = ttk.Button(button_frame, text="Редактировать", command=self._on_edit, state="disabled")
        self.edit_button.pack(side="left", padx=5)
        self.delete_button = ttk.Button(button_frame, text="Удалить", command=self._on_delete, state="disabled")
        self.delete_button.pack(side="left", padx=5)

        # Фрейм для Treeview и скроллбаров
        tree_frame = ttk.Frame(self, padding="10")
        tree_frame.pack(expand=True, fill="both")

        self.tree = ttk.Treeview(tree_frame, show="headings")  # show="headings" скрывает первый пустой столбец
        self.tree.pack(side="left", expand=True, fill="both")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)  # Событие выбора строки в таблице

        # Вертикальный скроллбар для Treeview
        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        # Горизонтальный скроллбар для Treeview (добавлен)
        scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)  # Помещаем под tree_frame
        scrollbar_x.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        self.tree.configure(xscrollcommand=scrollbar_x.set)

    def _load_table_names(self):
        """Загружает предопределенные имена таблиц в Combobox."""
        supported_tables = list(self.table_configs.keys())  # Используем ключи из table_configs
        self.table_combobox['values'] = supported_tables
        # Начальное значение current_table_name установится при выборе из combobox

    def _on_table_select_event(self, event=None):
        """Обработчик события выбора таблицы из Combobox."""
        # current_table_name уже обновлена через textvariable
        self._on_table_select()

    def _on_table_select(self):
        """Действия при выборе новой таблицы."""
        self.search_term.set("")  # Очищаем поле поиска
        self._load_data()  # Загружаем данные для выбранной таблицы
        self._update_button_states()  # Обновляем состояние кнопок

    def _on_search_change(self, event=None):
        """Обработчик изменения текста в поле поиска."""
        self._load_data()  # Перезагружаем данные с учетом поиска

    def _clear_treeview(self):
        """Очищает все строки и столбцы из Treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = ()

    def _load_data(self):
        """Загружает и отображает данные в Treeview для текущей таблицы и строки поиска."""
        self._clear_treeview()
        table_name = self.current_table_name.get()
        if not table_name:
            return

        search = self.search_term.get() if self.search_term.get() else None
        # Используем db_manager для получения данных (уже с JOIN'ами)
        data = self.db_manager.get_table_data(table_name, search_term=search)

        # Получаем список столбцов, которые НЕ нужно скрывать
        all_columns_from_db = self.db_manager.get_columns(table_name)  # Это вернет display names

        if data:
            # Колонки для отображения - это все ключи из первой строки данных,
            # за исключением тех, что указаны в self.hidden_columns_map
            hidden_for_current_table = self.hidden_columns_map.get(table_name, [])
            display_columns = [col for col in data[0].keys() if col not in hidden_for_current_table]

            self.tree["columns"] = display_columns
            for col_name in display_columns:
                self.tree.heading(col_name, text=col_name)
                self.tree.column(col_name, width=120, minwidth=80, anchor="w", stretch=tk.YES)  # Настройка столбцов

            for row_data_dict in data:
                # Значения для отображения в Treeview (только видимые столбцы)
                display_values = [row_data_dict[col] for col in display_columns]

                # 'iid' (item id) для Treeview - это фактический PK из БД.
                # В get_table_data первый столбец обычно имеет псевдоним 'ID' и является PK.
                item_pk_value = row_data_dict[self.table_configs[table_name]["pk_column_display"]]

                # Сохраняем весь словарь row_data_dict (включая скрытые ID) с элементом Treeview,
                # это понадобится для редактирования. Для этого используем user-defined tags.
                # Однако, прямой доступ к этим данным через теги не очень удобен.
                # Лучше использовать iid для идентификации и затем переполучать данные.
                self.tree.insert("", "end", iid=item_pk_value, values=display_values)
        else:  # Если данных нет (например, пустая таблица или результат поиска пуст)
            if all_columns_from_db:  # Если есть хотя бы заголовки
                self.tree["columns"] = all_columns_from_db
                for col_name in all_columns_from_db:
                    self.tree.heading(col_name, text=col_name)
                    self.tree.column(col_name, width=120, minwidth=80, anchor="w", stretch=tk.YES)

        self._update_button_states()

    def _on_tree_select(self, event=None):
        """Обработчик выбора строки в Treeview."""
        self._update_button_states()

    def _update_button_states(self):
        """Обновляет состояние кнопок (Редактировать, Удалить) в зависимости от выбора в Treeview."""
        selected_items = self.tree.selection()
        if selected_items:
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
        else:
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")

        # Кнопка "Добавить" активна, если выбрана таблица
        if self.current_table_name.get() and self.current_table_name.get() in self.table_configs:
            self.add_button.config(state="normal")
        else:
            self.add_button.config(state="disabled")

    def _get_selected_item_data(self):
        """
        Возвращает ID и полные данные выбранной строки из Treeview.
        Данные включают скрытые столбцы, необходимые для диалога редактирования.
        """
        selection = self.tree.selection()
        if not selection:
            return None, None  # Ничего не выбрано

        item_iid = selection[0]  # iid - это наш первичный ключ записи
        table_name = self.current_table_name.get()

        # Для получения полных данных (включая скрытые столбцы типа idproduct, idclient),
        # мы перезапрашиваем эту одну строку из БД.
        # Это гарантирует, что у нас есть все необходимые значения для initial_values диалога.
        # Можно было бы хранить полный dict при вставке в treeview, но перезапрос надежнее.
        all_data_for_table = self.db_manager.get_table_data(table_name, search_term=None)
        selected_row_data = None
        pk_display_name = self.table_configs[table_name]["pk_column_display"]

        for row in all_data_for_table:
            # Сравниваем значения PK. item_iid и row[pk_display_name] могут быть разных типов.
            if str(row[pk_display_name]) == str(item_iid):
                selected_row_data = row  # Это словарь со всеми полями, включая скрытые
                break

        return item_iid, selected_row_data

    def _on_add(self):
        """Обработчик нажатия кнопки 'Добавить'."""
        table_name = self.current_table_name.get()
        if not table_name or table_name not in self.table_configs:
            messagebox.showerror("Ошибка", "Таблица не настроена для добавления.", parent=self)
            return

        config = self.table_configs[table_name]
        # Передаем db_manager в диалог для загрузки данных в выпадающие списки
        dialog = AddEditDialog(self, f"Добавить запись в {table_name}", config["editable_fields"], self.db_manager)

        if dialog.result:  # Если диалог завершился с результатом (нажата OK)
            # dialog.result содержит ключи, которые могут быть отображаемыми именами или именами FK (idclient)
            if self.db_manager.insert_record(table_name, dialog.result):
                messagebox.showinfo("Успех", "Запись успешно добавлена.", parent=self)
                self._load_data()  # Обновляем таблицу
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить запись.", parent=self)

    def _on_edit(self):
        """Обработчик нажатия кнопки 'Редактировать'."""
        table_name = self.current_table_name.get()
        record_pk_value, selected_data_dict = self._get_selected_item_data()  # selected_data_dict содержит все поля

        if not record_pk_value or not selected_data_dict:
            messagebox.showwarning("Ошибка выбора", "Пожалуйста, выберите запись для редактирования.", parent=self)
            return

        if table_name not in self.table_configs:
            messagebox.showerror("Ошибка", f"Таблица '{table_name}' не настроена для редактирования.", parent=self)
            return

        config = self.table_configs[table_name]

        # Подготовка initial_values для диалога
        # Ключи в initial_dialog_values должны соответствовать ключам в config["editable_fields"]
        # или специальным ключам, которые AddEditDialog ожидает для FK (например, idclient).
        initial_dialog_values = {}
        for dialog_field_key, source_data_key in config["initial_value_keys"].items():
            if source_data_key in selected_data_dict:
                initial_dialog_values[dialog_field_key] = selected_data_dict[source_data_key]
            else:
                # Это может случиться, если source_data_key (например, "idproduct")
                # отсутствует в selected_data_dict, хотя должен быть.
                # Или если это поле не является обязательным.
                initial_dialog_values[dialog_field_key] = ""  # или None, в зависимости от логики диалога
                print(
                    f"Предупреждение: Ключ '{source_data_key}' не найден в selected_data_dict для поля '{dialog_field_key}' при редактировании.")

        dialog = AddEditDialog(self, f"Редактировать запись в {table_name}",
                               config["editable_fields"], self.db_manager, initial_values=initial_dialog_values)

        if dialog.result:
            # record_pk_value - это значение первичного ключа (например, ID из Treeview)
            if self.db_manager.update_record(table_name, record_pk_value, dialog.result):
                messagebox.showinfo("Успех", "Запись успешно обновлена.", parent=self)
                self._load_data()
            else:
                messagebox.showerror("Ошибка", "Не удалось обновить запись.", parent=self)

    def _on_delete(self):
        """Обработчик нажатия кнопки 'Удалить'."""
        table_name = self.current_table_name.get()
        record_pk_value, _ = self._get_selected_item_data()  # Нам нужен только PK для удаления

        if not record_pk_value:
            messagebox.showwarning("Ошибка выбора", "Пожалуйста, выберите запись для удаления.", parent=self)
            return

        pk_display_name = self.table_configs[table_name]["pk_column_display"]
        if messagebox.askyesno("Подтверждение удаления",
                               f"Вы уверены, что хотите удалить запись с {pk_display_name} {record_pk_value} из таблицы {table_name}?",
                               parent=self):
            if self.db_manager.delete_record(table_name, record_pk_value):
                messagebox.showinfo("Успех", "Запись успешно удалена.", parent=self)
                self._load_data()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить запись.", parent=self)
        self._update_button_states()  # Обновляем состояние кнопок

    def on_closing(self):
        """Обработчик закрытия главного окна (например, по крестику)."""
        if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
            self.db_manager.close()  # Корректно закрываем соединение с БД
            self.destroy()  # Уничтожаем окно Tkinter