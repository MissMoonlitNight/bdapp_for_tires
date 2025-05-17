# tire_mvc_app/view/main_view.py
import tkinter as tk
from tkinter import ttk, messagebox

from .dialogs_view import AddEditDialogView
from .sql_exec_view import SqlExecutionView


class MainView(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller # Сохраняем ссылку на контроллер
        self.title("Управление TireBD (MVC)")
        self.geometry("1100x750")

        self.current_table_name_var = tk.StringVar() # Для Combobox выбора таблицы
        self.search_term_var = tk.StringVar()        # Для поля поиска
        self.display_title_var = tk.StringVar()      # Для заголовка над Treeview
        self.display_title_var.set("Данные:")

        self._create_widgets()
        print("VIEW (MainView): Инициализирован.")

    def _create_widgets(self):
        """ Создает все виджеты главного окна. """
        # --- Верхняя панель управления ---
        top_controls_frame = ttk.Frame(self, padding="10")
        top_controls_frame.pack(fill="x")

        left_panel = ttk.Frame(top_controls_frame)
        left_panel.pack(side="left", fill="x", expand=True, padx=(0,10))

        table_select_frame = ttk.Frame(left_panel)
        table_select_frame.pack(fill="x", pady=(0,5))
        ttk.Label(table_select_frame, text="Выберите таблицу:").pack(side="left", padx=(0, 5))
        self.table_combobox = ttk.Combobox(table_select_frame, textvariable=self.current_table_name_var,
                                           state="readonly", width=20)
        self.table_combobox.pack(side="left", padx=(0, 10))
        # Привязываем событие к методу контроллера
        self.table_combobox.bind("<<ComboboxSelected>>",
                                 lambda event: self.controller.handle_table_selection_changed(self.current_table_name_var.get()))

        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Поиск:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_term_var, width=25)
        self.search_entry.pack(side="left", padx=(0, 5))
        self.search_button = ttk.Button(search_frame, text="Найти",
                                        command=lambda: self.controller.handle_search_button_clicked(
                                            self.current_table_name_var.get(), self.search_term_var.get()))
        self.search_button.pack(side="left")

        right_panel = ttk.Frame(top_controls_frame)
        right_panel.pack(side="right")

        crud_buttons_frame = ttk.Frame(right_panel)
        crud_buttons_frame.pack(fill="x", pady=(0,5))
        self.add_button = ttk.Button(crud_buttons_frame, text="Добавить", state="disabled",
                                     command=lambda: self.controller.handle_add_button_clicked(self.current_table_name_var.get()))
        self.add_button.pack(side="left", padx=2)
        self.edit_button = ttk.Button(crud_buttons_frame, text="Редактировать", state="disabled",
                                      command=lambda: self.controller.handle_edit_button_clicked(
                                          self.current_table_name_var.get(), self.get_selected_treeview_item_id()))
        self.edit_button.pack(side="left", padx=2)
        self.delete_button = ttk.Button(crud_buttons_frame, text="Удалить", state="disabled",
                                        command=lambda: self.controller.handle_delete_button_clicked(
                                            self.current_table_name_var.get(), self.get_selected_treeview_item_id()))
        self.delete_button.pack(side="left", padx=2)

        sql_button_frame = ttk.Frame(right_panel)
        sql_button_frame.pack(fill="x")
        self.sql_exec_button = ttk.Button(sql_button_frame, text="SQL Запросы",
                                          command=self.controller.handle_open_sql_execution_window_requested)
        self.sql_exec_button.pack(side="left", padx=2, fill="x")

        # --- Заголовок над таблицей ---
        self.display_title_label = ttk.Label(self, textvariable=self.display_title_var,
                                             font=("Arial", 12, "bold"))
        self.display_title_label.pack(pady=(10,0))

        # --- Treeview для отображения данных ---
        tree_frame = ttk.Frame(self, padding="10")
        tree_frame.pack(expand=True, fill="both")
        self.tree = ttk.Treeview(tree_frame, show="headings")
        self.tree.pack(side="left", expand=True, fill="both")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_item_selected) # Обновление состояния кнопок

        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        scrollbar_x.pack(side="bottom", fill="x", padx=10, pady=(0,10))
        self.tree.configure(xscrollcommand=scrollbar_x.set)

    def populate_table_combobox(self, table_names):
        """ Заполняет Combobox списком таблиц. """
        self.table_combobox['values'] = table_names
        print(f"VIEW (MainView): Combobox таблиц заполнен: {table_names}")

    def get_available_table_names(self):
        return self.table_combobox['values']

    def set_selected_table(self, table_name):
        if table_name in self.table_combobox['values']:
            self.current_table_name_var.set(table_name)
            print(f"VIEW (MainView): Программно выбрана таблица: {table_name}")


    def clear_search_term(self):
        """ Очищает поле ввода поиска. """
        self.search_term_var.set("")

    def display_data_in_treeview(self, data_list, column_names, display_title):
        """ Отображает данные в Treeview. """
        self._clear_treeview()
        self.display_title_var.set(display_title)

        if not column_names: # Если нет колонок (например, ошибка или пустой результат)
            print("VIEW (MainView): Нет колонок для отображения.")
            # Можно показать сообщение или оставить таблицу пустой
            if data_list and isinstance(data_list[0], dict) and ("Ошибка" in data_list[0] or "Информация" in data_list[0]):
                pass # Сообщение уже должно быть показано контроллером или SqlExecutionView
            return

        self.tree["columns"] = column_names
        for col_name in column_names:
            self.tree.heading(col_name, text=col_name)
            self.tree.column(col_name, width=120, minwidth=80, anchor="w", stretch=tk.YES)

        if data_list and isinstance(data_list[0], dict): # Убедимся, что данные - список словарей
            for row_data_dict in data_list:
                display_values = [row_data_dict.get(col, "") for col in column_names]
                # Для кастомных SQL iid не так важен, для таблиц он равен PK
                # Если в row_data_dict есть 'ID' (наш PK из get_table_data), используем его
                item_id = row_data_dict.get("ID", None)
                if item_id is not None:
                    self.tree.insert("", "end", iid=item_id, values=display_values)
                else: # Для результатов SQL без явного 'ID'
                    self.tree.insert("", "end", values=display_values)
        self._update_edit_delete_button_states() # Обновляем кнопки после загрузки данных

    def _clear_treeview(self):
        """ Очищает Treeview. """
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree["columns"] = ()

    def get_selected_treeview_item_id(self):
        """ Возвращает ID выбранного элемента в Treeview (iid). """
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _on_tree_item_selected(self, event=None):
        """ Обновляет состояние кнопок 'Редактировать' и 'Удалить' при выборе строки. """
        # Этот метод должен вызываться только в режиме просмотра таблицы
        if self.display_title_var.get().startswith("Данные таблицы:"):
            self._update_edit_delete_button_states()

    def _update_edit_delete_button_states(self):
        """ Обновляет состояние кнопок 'Редактировать' и 'Удалить'. """
        selected_item = self.get_selected_treeview_item_id()
        table_is_selected_for_crud = bool(self.current_table_name_var.get() and \
                                          self.current_table_name_var.get() in self.controller.table_configs)

        if table_is_selected_for_crud and selected_item:
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
        else:
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")

    def enable_crud_for_table_view(self):
        """ Активирует кнопки CRUD и Поиск для режима просмотра таблицы. """
        table_is_selected_for_crud = bool(self.current_table_name_var.get() and \
                                          self.current_table_name_var.get() in self.controller.table_configs)
        self.add_button.config(state="normal" if table_is_selected_for_crud else "disabled")
        self.search_button.config(state="normal" if table_is_selected_for_crud else "disabled")
        self._update_edit_delete_button_states() # Обновит Edit/Delete на основе выбора

    def disable_crud_for_custom_view(self):
        """ Деактивирует кнопки CRUD и Поиск для режима просмотра кастомных SQL-результатов. """
        self.add_button.config(state="disabled")
        self.edit_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.search_button.config(state="disabled")

    # --- Методы для открытия диалоговых окон ---
    def open_add_edit_dialog(self, title, fields_config, initial_values=None, db_manager_for_dialog_fk=None, current_table_name_for_dialog=None):
        """ Открывает диалог добавления/редактирования и возвращает введенные данные. """
        # Здесь мы используем AddEditDialogView из dialogs_view.py
        dialog = AddEditDialogView(self, title, fields_config,
                                   db_manager_for_dialog_fk, # Передаем db_manager для FK
                                   initial_values,
                                   current_table_name_for_dialog)
        # AddEditDialogView сам будет модальным и вернет результат в self.result
        # Этот метод должен ждать закрытия диалога и возвращать dialog.result
        self.wait_window(dialog) # Ждем, пока диалог не будет закрыт
        return dialog.result # dialog.result устанавливается в _on_ok или _on_cancel диалога

    def open_sql_execution_view(self, db_manager, display_callback):
        """ Открывает окно для выполнения SQL-запросов. """
        # Передаем контроллер, чтобы SqlExecutionView мог вызывать его методы для выполнения SQL
        SqlExecutionView(self, self.controller) # SqlExecutionView будет использовать self.controller