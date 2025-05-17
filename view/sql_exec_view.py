# tire_mvc_app/view/sql_exec_view.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


class SqlExecutionView(tk.Toplevel):
    def __init__(self, parent, controller):  # Принимает parent (MainView) и controller
        super().__init__(parent)
        self.transient(parent)
        self.title("Выполнение SQL Запросов")
        self.controller = controller  # Сохраняем ссылку на контроллер
        self.geometry("450x250")

        self._create_widgets()
        self.grab_set()  # Модальность

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill="both")
        ttk.Label(main_frame, text="Выберите действие:", font=("Arial", 12)).pack(pady=(0, 15))

        btn_order_info = ttk.Button(main_frame, text="1. Информация о заказе (ID)", width=35,
                                    command=self._execute_order_info_clicked)
        btn_order_info.pack(pady=5, ipady=5)

        btn_sold_tires = ttk.Button(main_frame, text="2. Кол-во проданных шин (период)", width=35,
                                    command=self._execute_sold_tires_clicked)
        btn_sold_tires.pack(pady=5, ipady=5)

        btn_products_by_cat = ttk.Button(main_frame, text="3. Продукты (категория, цены)", width=35,
                                         command=self._execute_products_by_cat_clicked)
        btn_products_by_cat.pack(pady=5, ipady=5)

    def _execute_order_info_clicked(self):
        order_id = simpledialog.askinteger("ID Заказа", "Введите ID заказа:", parent=self)
        if order_id is not None:
            # Вызываем метод контроллера
            success = self.controller.execute_sql_order_info(order_id)
            if success: self.destroy()  # Закрываем, если результат отображен в главном окне

    def _execute_sold_tires_clicked(self):
        date_start = simpledialog.askstring("Начало периода", "Введите дату (ГГГГ-ММ-ДД):", parent=self)
        if date_start is None: return
        date_end = simpledialog.askstring("Конец периода", "Введите дату (ГГГГ-ММ-ДД):", parent=self)
        if date_end is None: return
        # Вызываем метод контроллера
        self.controller.execute_sql_sold_tires_count(date_start, date_end)

    def _execute_products_by_cat_clicked(self):
        categories = ["Болты", "Диски", "Шины"]
        category = simpledialog.askstring("Категория", f"Введите ({', '.join(categories)}):", parent=self)
        if category is None or category not in categories:
            if category is not None: messagebox.showwarning("Ошибка", "Неверная категория.", parent=self)
            return
        min_sum_str = simpledialog.askstring("Мин. сумма", "Введите:", parent=self)
        if min_sum_str is None: return
        max_sum_str = simpledialog.askstring("Макс. сумма", "Введите:", parent=self)
        if max_sum_str is None: return

        try:
            min_sum, max_sum = float(min_sum_str), float(max_sum_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Суммы должны быть числами.", parent=self); return
        if min_sum > max_sum: messagebox.showwarning("Ошибка", "Мин > Макс.", parent=self); return

        # Вызываем метод контроллера
        success = self.controller.execute_sql_products_by_category(category, min_sum, max_sum)
        if success: self.destroy()