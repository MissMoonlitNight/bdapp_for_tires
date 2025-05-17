# tire_mvc_app/main.py
import tkinter as tk # Для messagebox, если контроллер или модель напрямую его не вызывают
from tkinter import messagebox
# Относительные импорты, если main.py находится в корневой папке проекта tire_mvc_app
from models.database_manager import DatabaseManager
from view.main_view import MainView
from controller.app_controller import AppController

class Application:
    def __init__(self):
        # 1. Создание Модели
        self.db_manager = DatabaseManager()
        if not self.db_manager.connection or not self.db_manager.connection.is_connected():

            # Показываем сообщение об ошибке, если нет подключения к БД
            print("CRITICAL: Не удалось подключиться к базе данных. Приложение не может быть запущено.")
            root_temp = tk.Tk()
            root_temp.withdraw()
            messagebox.showerror("Ошибка подключения к БД",
                                 "Не удалось подключиться к базе данных. Проверьте конфигурацию и доступность сервера. Приложение будет закрыто.")
            root_temp.destroy()
            return

        # 2. Создание Контроллера
        self.controller = AppController(self.db_manager)

        # 3. Создание Вида
        self.main_view = MainView(self.controller)
        self.controller.set_view(self.main_view)

        self.main_view.protocol("WM_DELETE_WINDOW", self.on_closing)

        print("Приложение инициализировано (Model, View, Controller).")

    def run(self):
        """ Запускает главный цикл приложения, если инициализация прошла успешно. """
        if hasattr(self, 'main_view') and self.main_view: # Проверка, что main_view создано
            self.main_view.mainloop()
        else:
            print("Приложение не было запущено из-за ошибки инициализации (вероятно, БД).")

    def on_closing(self):
        """ Обработчик закрытия главного окна. """
        if messagebox.askokcancel("Выход", "Вы действительно хотите выйти?"):
            print("Закрытие приложения...")
            self.db_manager.close() # Закрываем соединение с БД через модель
            if hasattr(self, 'main_view') and self.main_view:
                self.main_view.destroy() # Уничтожаем главное окно
            print("Приложение закрыто.")


if __name__ == "__main__":
    app = Application()
    app.run()