from main_app import MainApp
from database_manager import DatabaseManager

if __name__ == "__main__":
    # Создаем экземпляр менеджера базы данных
    db_manager = DatabaseManager()

    # Запускаем приложение только если соединение с БД успешно установлено
    if db_manager.connection and db_manager.connection.is_connected():
        app = MainApp(db_manager)
        # Устанавливаем обработчик для кнопки закрытия окна
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop() # Запускаем главный цикл Tkinter
    else:
        print("Не удалось подключиться к базе данных. Приложение не будет запущено.")
        # Можно добавить здесь GUI-сообщение об ошибке, если Tkinter уже инициализирован
        # или если db_manager._connect() возвращает статус для более детальной обработки.