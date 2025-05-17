
from tkinter import simpledialog, messagebox # Для простых диалогов и сообщений

# Импортируем классы View, которые будут создаваться в main.py и передаваться сюда
# Для type hinting или если будем создавать View из контроллера (не лучший MVC-подход, но возможно)
# from view.main_view import MainView
# from view.dialogs_view import AddEditDialogView # Если диалоги вынесены
# from view.sql_exec_view import SqlExecutionView


class AppController:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.main_view = None # Ссылка на главный вид будет установлена из main.py

        self.table_configs = {
            "client": {
                "pk_column_display": "ID",
                "pk_db_col": "idclient",
                "editable_fields": {"FIO": "text", "Адрес": "text", "Телефон": "text"},
                "initial_value_keys": {"FIO": "FIO", "Адрес": "Адрес", "Телефон": "Телефон"},
                "db_columns_map": {"FIO": "FIO", "Адрес": "address", "Телефон": "phone number"}
            },
            "tires": {
                "pk_column_display": "ID",
                "pk_db_col": "idtires",
                "editable_fields": {"Тип": "text", "Сезон": "text", "Модель": "text", "Цена_Продукта": "text"},
                "initial_value_keys": {"Тип": "Тип", "Сезон": "Сезон", "Модель": "Модель",
                                       "Цена_Продукта": "Цена_Продукта", "idproduct": "idproduct"},
                "db_columns_map": {"Тип": "type", "Сезон": "season", "Модель": "model"} # Цена обрабатывается отдельно
            },
            "order": {
                "pk_column_display": "ID",
                "pk_db_col": "idorder",
                "editable_fields": {"Дата": "text", "Статус": "text",
                                    "ФИО_Клиента": {"type": "dropdown", "source": "clients"},
                                    "ФИО_Сотрудника": {"type": "dropdown", "source": "employees"}},
                "initial_value_keys": {"Дата": "Дата", "Статус": "Статус",
                                       "ФИО_Клиента": "idclient", "ФИО_Сотрудника": "idemployee"},
                "db_columns_map": {"Дата": "date", "Статус": "status",
                                   "idclient": "idclient", "idemployee": "idemployee"}
            }
        }
        # Скрытые столбцы
        self.hidden_columns_map = {
            "tires": ["idproduct", "idshipment"],
            "order": ["idclient", "idemployee"]
        }
        print("CONTROLLER: Инициализирован.")

    def set_view(self, main_view):
        """ Устанавливает ссылку на главный вид. """
        self.main_view = main_view
        print("CONTROLLER: Вид установлен.")
        # После установки вида, можно загрузить начальные данные, если это требуется
        self.load_initial_table_list()
        # И если список таблиц не пуст, выбрать первую и загрузить ее данные
        if self.main_view and self.main_view.get_available_table_names():
             first_table = self.main_view.get_available_table_names()[0]
             self.main_view.set_selected_table(first_table) # Установить в Combobox
             self.handle_table_selection_changed(first_table) # Загрузить данные


    def load_initial_table_list(self):
        """ Загружает список доступных таблиц в View. """
        if self.main_view:
            table_names = list(self.table_configs.keys())
            self.main_view.populate_table_combobox(table_names)
            print(f"CONTROLLER: Список таблиц загружен в View: {table_names}")

    def handle_table_selection_changed(self, table_name):
        """ Обрабатывает выбор таблицы в Combobox. """
        print(f"CONTROLLER: Выбрана таблица '{table_name}'. Загрузка данных...")
        if self.main_view and table_name:
            self.main_view.clear_search_term() # Очищаем поиск при смене таблицы
            data = self.db_manager.get_table_data(table_name, search_term=None)
            columns = self.db_manager.get_display_columns_for_table(table_name, self.table_configs, self.hidden_columns_map)
            self.main_view.display_data_in_treeview(data, columns, f"Данные таблицы: {table_name.capitalize()}")
            self.main_view.enable_crud_for_table_view() # Активируем CRUD кнопки
            print(f"CONTROLLER: Данные для '{table_name}' загружены и отображены.")

    def handle_search_button_clicked(self, table_name, search_term):
        """ Обрабатывает нажатие кнопки 'Найти'. """
        print(f"CONTROLLER: Поиск в таблице '{table_name}' по запросу '{search_term}'.")
        if self.main_view and table_name:
            data = self.db_manager.get_table_data(table_name, search_term)
            columns = self.db_manager.get_display_columns_for_table(table_name, self.table_configs, self.hidden_columns_map)
            self.main_view.display_data_in_treeview(data, columns, f"Результаты поиска в: {table_name.capitalize()}")
            self.main_view.enable_crud_for_table_view()
            print(f"CONTROLLER: Результаты поиска отображены.")

    def handle_add_button_clicked(self, table_name):
        """ Обрабатывает нажатие кнопки 'Добавить'. """
        print(f"CONTROLLER: Запрос на добавление записи в таблицу '{table_name}'.")
        if not table_name or table_name not in self.table_configs:
            messagebox.showerror("Ошибка", "Таблица не выбрана или не настроена для добавления.")
            return

        config = self.table_configs[table_name]
        # View должен предоставить метод для открытия диалога добавления
        # и вернуть собранные данные.
        dialog_data = self.main_view.open_add_edit_dialog(
            title=f"Добавить запись в {table_name}",
            fields_config=config["editable_fields"],
            db_manager_for_dialog_fk=self.db_manager, # Для FK dropdowns
            current_table_name_for_dialog=table_name
        )

        if dialog_data: # Если пользователь ввел данные и нажал OK
            if self.db_manager.insert_record(table_name, dialog_data, self.table_configs):
                messagebox.showinfo("Успех", "Запись успешно добавлена.")
                self.handle_table_selection_changed(table_name) # Обновляем данные в таблице
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить запись.")
        print(f"CONTROLLER: Процесс добавления завершен.")


    def handle_edit_button_clicked(self, table_name, selected_item_id_in_view):
        """ Обрабатывает нажатие кнопки 'Редактировать'. """
        print(f"CONTROLLER: Запрос на редактирование записи ID '{selected_item_id_in_view}' в таблице '{table_name}'.")
        if not table_name or table_name not in self.table_configs:
            messagebox.showerror("Ошибка", "Таблица не выбрана или не настроена для редактирования.")
            return
        if not selected_item_id_in_view:
            messagebox.showwarning("Ошибка выбора", "Пожалуйста, выберите запись для редактирования.")
            return

        config = self.table_configs[table_name]
        # Получаем полные данные для выбранной строки (включая скрытые ID)
        all_data_for_table = self.db_manager.get_table_data(table_name)
        initial_data_for_dialog = None
        pk_display_name = config["pk_column_display"] # 'ID'

        for row in all_data_for_table:
            if str(row[pk_display_name]) == str(selected_item_id_in_view):
                initial_data_for_dialog_raw = row
                break
        else: # Если строка не найдена (маловероятно, но возможно)
            messagebox.showerror("Ошибка", "Выбранная запись не найдена в базе данных.")
            return

        # Подготовка initial_values для диалога на основе initial_value_keys
        initial_values_mapped = {}
        for dialog_field_key, source_data_key in config["initial_value_keys"].items():
            initial_values_mapped[dialog_field_key] = initial_data_for_dialog_raw.get(source_data_key, "")

        dialog_data = self.main_view.open_add_edit_dialog(
            title=f"Редактировать запись в {table_name}",
            fields_config=config["editable_fields"],
            initial_values=initial_values_mapped,
            db_manager_for_dialog_fk=self.db_manager,
            current_table_name_for_dialog=table_name
        )

        if dialog_data:
            # record_id для db_manager.update_record - это фактический PK (selected_item_id_in_view)
            if self.db_manager.update_record(table_name, selected_item_id_in_view, dialog_data, self.table_configs):
                messagebox.showinfo("Успех", "Запись успешно обновлена.")
                self.handle_table_selection_changed(table_name) # Обновляем данные
            else:
                messagebox.showerror("Ошибка", "Не удалось обновить запись.")
        print(f"CONTROLLER: Процесс редактирования завершен.")


    def handle_delete_button_clicked(self, table_name, selected_item_id_in_view):
        """ Обрабатывает нажатие кнопки 'Удалить'. """
        print(f"CONTROLLER: Запрос на удаление записи ID '{selected_item_id_in_view}' из таблицы '{table_name}'.")
        if not table_name or table_name not in self.table_configs:
            messagebox.showerror("Ошибка", "Таблица не выбрана или не настроена для удаления.")
            return
        if not selected_item_id_in_view:
            messagebox.showwarning("Ошибка выбора", "Пожалуйста, выберите запись для удаления.")
            return

        pk_display_name = self.table_configs[table_name]["pk_column_display"]
        if messagebox.askyesno("Подтверждение удаления",
                                f"Вы уверены, что хотите удалить запись с {pk_display_name} {selected_item_id_in_view} из таблицы {table_name}?"):
            if self.db_manager.delete_record(table_name, selected_item_id_in_view, self.table_configs):
                messagebox.showinfo("Успех", "Запись успешно удалена.")
                self.handle_table_selection_changed(table_name) # Обновляем данные
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить запись.")
        print(f"CONTROLLER: Процесс удаления завершен.")

    def handle_open_sql_execution_window_requested(self):
        """ Обрабатывает запрос на открытие окна выполнения SQL. """
        print(f"CONTROLLER: Запрос на открытие окна SQL-запросов.")
        self.main_view.open_sql_execution_view(self.db_manager, self.handle_display_custom_sql_result)


    def handle_display_custom_sql_result(self, data, title):
        """ Обрабатывает результат кастомного SQL и передает его в View. """
        print(f"CONTROLLER: Отображение кастомных SQL результатов: {title}")
        if self.main_view:
            self.main_view.display_data_in_treeview(data, list(data[0].keys()) if data and data[0] else [], title)
            self.main_view.disable_crud_for_custom_view() # Отключаем CRUD для этого вида

    # --- Обработчики для конкретных SQL-запросов из SqlExecutionView ---
    # Эти методы будут вызываться из SqlExecutionView через контроллер

    def execute_sql_order_info(self, order_id):
        """ Выполняет SQL-запрос "Информация о заказе". """
        print(f"CONTROLLER: SQL - Информация о заказе ID: {order_id}")
        result = self.db_manager.call_get_order_information(order_id)
        self.handle_display_custom_sql_result(result, f"Информация по заказу ID: {order_id}")
        return bool(result and not ("Ошибка" in result[0] if result[0] else True)) # true если нет ошибок и есть результат

    def execute_sql_sold_tires_count(self, date_start, date_end):
        """ Выполняет SQL-запрос "Кол-во проданных шин". """
        print(f"CONTROLLER: SQL - Кол-во проданных шин: {date_start} - {date_end}")
        result = self.db_manager.call_get_sold_tires_count_in_period(date_start, date_end)
        if isinstance(result, (int, float)):
            messagebox.showinfo("Количество проданных шин",
                                f"За период с {date_start} по {date_end} продано шин: {result}")
        else: # Строка с ошибкой
            messagebox.showerror("Ошибка", str(result))

    def execute_sql_products_by_category(self, category, min_sum, max_sum):
        """ Выполняет SQL-запрос "Продукты по категории и цене". """
        print(f"CONTROLLER: SQL - Продукты: {category}, Цены: {min_sum}-{max_sum}")
        result = self.db_manager.call_get_product_by_categories(category, min_sum, max_sum)
        self.handle_display_custom_sql_result(result, f"Продукты: {category}, Цена: {min_sum:.2f}-{max_sum:.2f}")
        return bool(result and not ("Ошибка" in result[0] if result[0] else True))