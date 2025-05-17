# tire_app/database_manager.py
import mysql.connector
from db_config import DB_CONFIG

class DatabaseManager:
    """
    Класс для управления всеми взаимодействиями с базой данных.
    Реализует паттерн Repository или Data Access Object (DAO).
    """
    def __init__(self):
        self.config = DB_CONFIG
        self.connection = None
        self.cursor = None
        self._connect() # Подключаемся при инициализации

    def _connect(self):
        """
        Устанавливает соединение с базой данных.
        """
        try:
            self.connection = mysql.connector.connect(**self.config)
            # dictionary=True позволяет получать результаты запросов в виде словарей,
            # где ключи - это имена столбцов. Это очень удобно.
            self.cursor = self.connection.cursor(dictionary=True)
            print("Успешное подключение к базе данных.")
        except mysql.connector.Error as err:
            print(f"Ошибка подключения к базе данных: {err}")
            # В реальном приложении здесь может быть более сложная обработка ошибок.
            self.connection = None
            self.cursor = None

    def close(self):
        """
        Закрывает соединение с базой данных, если оно открыто.
        """
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("Соединение с базой данных закрыто.")

    def _execute_query(self, query, params=None, fetch=True):
        """
        Приватный вспомогательный метод для выполнения SQL-запросов.

        :param query: SQL-запрос (строка).
        :param params: Параметры для запроса (кортеж или список).
        :param fetch: True, если нужно получить результаты (SELECT), False для INSERT/UPDATE/DELETE.
        :return: Список словарей (для SELECT) или True/False (для INSERT/UPDATE/DELETE).
        """
        if not self.cursor:
            print("Курсор базы данных недоступен.")
            return None if fetch else False
        try:
            self.cursor.execute(query, params)
            if fetch:
                return self.cursor.fetchall() # Получаем все строки результата
            else:
                self.connection.commit() # Подтверждаем изменения для INSERT, UPDATE, DELETE
                return True
        except mysql.connector.Error as err:
            print(f"Ошибка выполнения запроса к БД: {err}")
            if self.connection and not fetch: # Откатываем изменения при ошибке для не-SELECT запросов
                self.connection.rollback()
            return None if fetch else False

    def get_table_data(self, table_name, search_term=None):
        """
        Получает данные из указанной таблицы с возможностью поиска.
        Использует JOIN для отображения связанных данных вместо ID.

        :param table_name: Имя таблицы ('client', 'tires', 'order').
        :param search_term: Строка для поиска (опционально).
        :return: Список словарей с данными или пустой список.
        """
        query = ""
        params = []

        # Определяем базовые запросы и поля для поиска для каждой таблицы.
        # Здесь происходят JOIN'ы и присвоение псевдонимов столбцам (AS).
        if table_name == "client":
            query = 'SELECT idclient AS ID, FIO, address AS Адрес, `phone number` AS Телефон FROM client'
            search_fields = ["FIO", "address", "`phone number`"] # Поля для поиска
        elif table_name == "tires":
            query = """
                SELECT
                    t.idtires AS ID,
                    t.type AS Тип,
                    t.season AS Сезон,
                    t.model AS Модель,
                    p.sum AS Цена_Продукта,
                    s.address AS Адрес_Поставки,
                    t.idproduct  -- Сохраняем для редактирования/внутреннего использования
                FROM tires t
                JOIN product p ON t.idproduct = p.idproduct
                JOIN shipment s ON p.idshipment = s.idshipment
            """
            search_fields = ["t.type", "t.season", "t.model", "p.sum", "s.address"]
        elif table_name == "order": # 'order' - зарезервированное слово, используем обратные кавычки
            query = """
                SELECT
                    o.idorder AS ID,
                    o.date AS Дата,
                    o.status AS Статус,
                    c.FIO AS ФИО_Клиента,
                    e.FIO AS ФИО_Сотрудника,
                    o.idclient,  -- Сохраняем для редактирования/внутреннего использования
                    o.idemployee -- Сохраняем для редактирования/внутреннего использования
                FROM `order` o
                JOIN client c ON o.idclient = c.idclient
                JOIN employee e ON o.idemployee = e.idemployee
            """
            search_fields = ["o.date", "o.status", "c.FIO", "e.FIO"]
        else:
            print(f"Данные для таблицы '{table_name}' не настроены.")
            return []

        if search_term:
            # Формируем условие WHERE для поиска по нескольким полям
            conditions = " OR ".join([f"{field} LIKE %s" for field in search_fields])
            query += f" WHERE {conditions}"
            params = [f"%{search_term}%"] * len(search_fields) # Параметры для LIKE

        query += " ORDER BY ID ASC" # Сортировка для консистентности

        return self._execute_query(query, params)

    def get_columns(self, table_name):
        """
        Получает имена столбцов для отображения в Treeview.
        Возвращает псевдонимы (display names), если они определены.
        """
        # Для простоты, получаем одну строку данных и извлекаем ключи словаря.
        # Более надежный способ - явно определить эти сопоставления.
        data = self.get_table_data(table_name) # Получаем данные с псевдонимами
        if data:
            # Исключаем скрытые столбцы (внутренние ID) из отображаемых заголовков
            hidden_cols_map = {
                "tires": ["idproduct"],
                "order": ["idclient", "idemployee"]
            }
            hidden_for_current_table = hidden_cols_map.get(table_name, [])
            return [col for col in data[0].keys() if col not in hidden_for_current_table]

        # Запасной вариант для пустых таблиц или если get_table_data не вернул данные
        # (но get_table_data должен быть настроен для всех поддерживаемых таблиц)
        if table_name == "client": return ["ID", "FIO", "Адрес", "Телефон"]
        if table_name == "tires": return ["ID", "Тип", "Сезон", "Модель", "Цена_Продукта", "Адрес_Поставки"]
        if table_name == "order": return ["ID", "Дата", "Статус", "ФИО_Клиента", "ФИО_Сотрудника"]
        return []


    def insert_record(self, table_name, data_dict):
        """
        Вставляет новую запись в указанную таблицу.

        :param table_name: Имя таблицы.
        :param data_dict: Словарь, где ключи - это отображаемые имена полей (из диалога),
                          а значения - вводимые данные.
        :return: True в случае успеха, False в противном случае.
        """
        # Карта для преобразования отображаемых имен полей (из диалога)
        # в реальные имена столбцов БД. Также определяет, какие поля ожидаются.
        db_columns_map = {
            "client": {"FIO": "FIO", "Адрес": "address", "Телефон": "phone number"},
            "tires": {"Тип": "type", "Сезон": "season", "Модель": "model", "idproduct": "idproduct"},
            "order": {"Дата": "date", "Статус": "status", "idclient": "idclient", "idemployee": "idemployee"}
        }

        if table_name not in db_columns_map:
            print(f"Вставка не настроена для таблицы {table_name}")
            return False

        actual_data_to_insert = {}
        for display_key, db_key in db_columns_map[table_name].items():
            if display_key in data_dict: # Если ключ есть в data_dict (например, "ФИО")
                 actual_data_to_insert[db_key] = data_dict[display_key]
            # Для внешних ключей (FK), если они передаются напрямую с именем столбца БД (например, 'idproduct')
            elif db_key in data_dict and db_key in ["idproduct", "idclient", "idemployee"]:
                 actual_data_to_insert[db_key] = data_dict[db_key]

        if not actual_data_to_insert:
            print("Не предоставлены корректные данные для вставки.")
            return False

        # Используем обратные кавычки для имен столбцов на случай, если они содержат пробелы или являются ключевыми словами
        cols = ", ".join([f"`{col}`" for col in actual_data_to_insert.keys()])
        placeholders = ", ".join(["%s"] * len(actual_data_to_insert)) # Заполнители для значений
        query = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"

        return self._execute_query(query, list(actual_data_to_insert.values()), fetch=False)

    def update_record(self, table_name, record_id, data_dict):
        """
        Обновляет существующую запись в таблице.

        :param table_name: Имя таблицы.
        :param record_id: ID обновляемой записи.
        :param data_dict: Словарь с обновляемыми данными (ключи - отображаемые имена или имена столбцов БД).
        :return: True в случае успеха, False в противном случае.
        """
        pk_column = "" # Имя столбца первичного ключа
        db_columns_map = {} # Карта отображаемых имен на имена столбцов БД

        if table_name == "client":
            pk_column = "idclient"
            db_columns_map = {"FIO": "FIO", "Адрес": "address", "Телефон": "phone number"}
        elif table_name == "tires":
            pk_column = "idtires"
            db_columns_map = {"Тип": "type", "Сезон": "season", "Модель": "model", "idproduct": "idproduct"}
        elif table_name == "order":
            pk_column = "idorder"
            db_columns_map = {"Дата": "date", "Статус": "status", "idclient": "idclient", "idemployee": "idemployee"}
        else:
            print(f"Обновление не настроено для таблицы {table_name}")
            return False

        actual_data_to_update = {}
        for display_key, db_key in db_columns_map.items():
            if display_key in data_dict:
                actual_data_to_update[db_key] = data_dict[display_key]
            elif db_key in data_dict and db_key in ["idproduct", "idclient", "idemployee"]: # Для FK
                 actual_data_to_update[db_key] = data_dict[db_key]

        if not actual_data_to_update:
            print("Не предоставлены корректные данные для обновления.")
            return False

        set_clause = ", ".join([f"`{col}` = %s" for col in actual_data_to_update.keys()])
        query = f"UPDATE `{table_name}` SET {set_clause} WHERE `{pk_column}` = %s"
        params = list(actual_data_to_update.values()) + [record_id] # Значения и ID для WHERE

        return self._execute_query(query, params, fetch=False)

    def delete_record(self, table_name, record_id):
        """
        Удаляет запись из таблицы.

        :param table_name: Имя таблицы.
        :param record_id: ID удаляемой записи.
        :return: True в случае успеха, False в противном случае.
        """
        pk_column = ""
        if table_name == "client": pk_column = "idclient"
        elif table_name == "tires": pk_column = "idtires"
        elif table_name == "order": pk_column = "idorder" # Имя таблицы `order` в кавычках
        else:
            print(f"Удаление не настроено для таблицы {table_name}")
            return False

        query = f"DELETE FROM `{table_name}` WHERE `{pk_column}` = %s"
        return self._execute_query(query, (record_id,), fetch=False)

    # Вспомогательные методы для заполнения выпадающих списков в диалогах добавления/редактирования
    def get_clients_for_dropdown(self):
        """Получает список клиентов (ID, ФИО) для выпадающего списка."""
        query = "SELECT idclient, FIO FROM client ORDER BY FIO"
        return self._execute_query(query)

    def get_employees_for_dropdown(self):
        """Получает список сотрудников (ID, ФИО) для выпадающего списка."""
        query = "SELECT idemployee, FIO FROM employee ORDER BY FIO"
        return self._execute_query(query)

    def get_products_for_dropdown(self):
        """
        Получает список продуктов (ID, описание) для выпадающего списка.
        Описание формируется из категории, ID и цены продукта.
        """
        query = """
            SELECT
                p.idproduct,
                CONCAT(ipc.name, ' - ID: ', p.idproduct, ' (Цена: ', p.sum, ')') AS description
            FROM product p
            JOIN id_product_categories ipc ON p.idproduct_categories = ipc.idid_product_categories
            ORDER BY p.idproduct
        """
        return self._execute_query(query)