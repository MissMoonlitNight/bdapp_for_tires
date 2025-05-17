# tire_mvc_app/model/database_manager.py
import mysql.connector
from datetime import datetime  # Для преобразования дат
from db_config import DB_CONFIG  # Путь от корня проекта


class DatabaseManager:
    """
    Класс для управления всеми взаимодействиями с базой данных.
    """

    def __init__(self):
        self.config = DB_CONFIG
        self.connection = None
        self.cursor = None
        self._connect()

    def _connect(self):
        """ Устанавливает соединение с базой данных. """
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            print("MODEL: Успешное подключение к базе данных.")
        except mysql.connector.Error as err:
            print(f"MODEL: Ошибка подключения к базе данных: {err}")
            self.connection = None
            self.cursor = None

    def close(self):
        """ Закрывает соединение с базой данных. """
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("MODEL: Соединение с базой данных закрыто.")

    def _execute_query(self, query, params=None, fetch=True):
        """ Приватный метод для выполнения SQL-запросов. """
        if not self.cursor:
            print("MODEL: Курсор базы данных недоступен.")
            return None if fetch else False
        try:
            self.cursor.execute(query, params)
            if fetch:
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return True
        except mysql.connector.Error as err:
            print(f"MODEL: Ошибка выполнения запроса к БД: {query} - {err}")
            if self.connection and not fetch:
                self.connection.rollback()
            return None if fetch else False

    def get_table_data(self, table_name, search_term=None):
        """ Получает данные таблицы с возможностью поиска (для основного TreeView). """
        query = ""
        params = []
        # Определяем запросы для каждой таблицы
        if table_name == "client":
            query = 'SELECT idclient AS ID, FIO, address AS Адрес, `phone number` AS Телефон FROM client'
            search_fields = ["FIO", "address", "`phone number`"]
        elif table_name == "tires":
            query = """
                SELECT t.idtires AS ID, t.type AS Тип, t.season AS Сезон, t.model AS Модель,
                       p.sum AS Цена_Продукта, s.address AS Адрес_Поставки,
                       t.idproduct, p.idshipment 
                FROM tires t
                JOIN product p ON t.idproduct = p.idproduct
                LEFT JOIN shipment s ON p.idshipment = s.idshipment
            """
            search_fields = ["t.type", "t.season", "t.model", "p.sum", "s.address"]
        elif table_name == "order":
            query = """
                SELECT o.idorder AS ID, o.date AS Дата, o.status AS Статус,
                       c.FIO AS ФИО_Клиента, e.FIO AS ФИО_Сотрудника,
                       o.idclient, o.idemployee 
                FROM `order` o
                JOIN client c ON o.idclient = c.idclient
                JOIN employee e ON o.idemployee = e.idemployee
            """
            search_fields = ["o.date", "o.status", "c.FIO", "e.FIO"]
        else:
            return []  # Неизвестная таблица

        if search_term:
            conditions = " OR ".join([f"{field} LIKE %s" for field in search_fields])
            query += f" WHERE {conditions}"
            params = [f"%{search_term}%"] * len(search_fields)
        query += " ORDER BY ID ASC"
        return self._execute_query(query, params)

    def get_display_columns_for_table(self, table_name, all_table_configs, hidden_columns_map):
        """
        Возвращает список имен столбцов для отображения в TreeView для конкретной таблицы.
        Использует конфигурации для определения видимых столбцов.
        """
        # Сначала пытаемся получить данные, чтобы определить колонки из реального запроса
        sample_data = self.get_table_data(table_name)
        if sample_data and isinstance(sample_data, list) and len(sample_data) > 0 and isinstance(sample_data[0], dict):
            all_cols_from_query = list(sample_data[0].keys())
            hidden_for_current_table = hidden_columns_map.get(table_name, [])
            return [col for col in all_cols_from_query if col not in hidden_for_current_table]

        if table_name in all_table_configs:
            print(f"MODEL: Не удалось получить структуру столбцов для таблицы '{table_name}' из данных.")

        if table_name == "client": return ["ID", "FIO", "Адрес", "Телефон"]
        if table_name == "tires": return ["ID", "Тип", "Сезон", "Модель", "Цена_Продукта", "Адрес_Поставки"]
        if table_name == "order": return ["ID", "Дата", "Статус", "ФИО_Клиента", "ФИО_Сотрудника"]
        return []

    def _create_product_for_tire(self, price, shipment_id=1):
        """ Создает запись в 'product' для новой шины (категория 3). """
        id_category_tires = 3
        default_shipment_id = shipment_id  # ВАЖНО: product.idshipment NOT NULL
        try:
            self.cursor.execute("SELECT idshipment FROM shipment WHERE idshipment = %s", (default_shipment_id,))
            if not self.cursor.fetchone():
                self.cursor.execute("INSERT IGNORE INTO shipment (idshipment, address, status) VALUES (%s, %s, %s)",
                                    (default_shipment_id, "Авто-отгрузка для шин", "Ожидает"))
                self.connection.commit()
        except mysql.connector.Error as err:
            print(f"MODEL: Ошибка при обеспечении отгрузки: {err}");
            return None

        query = "INSERT INTO product (sum, idproduct_categories, idshipment) VALUES (%s, %s, %s)"
        try:
            self.cursor.execute(query, (price, id_category_tires, default_shipment_id))
            self.connection.commit()
            return self.cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"MODEL: Ошибка при создании продукта для шины: {err}");
            self.connection.rollback();
            return None

    def _update_product_price(self, idproduct, new_price):
        """ Обновляет цену продукта. """
        return self._execute_query("UPDATE product SET sum = %s WHERE idproduct = %s", (new_price, idproduct),
                                   fetch=False)

    def insert_tire_with_product(self, tire_data_from_dialog, product_price):
        """ Вставляет новую шину: сначала продукт, потом шину. """
        idproduct = self._create_product_for_tire(product_price)
        if not idproduct: return False

        # Ключи в tire_data_from_dialog - это отображаемые имена ('Тип', 'Сезон', 'Модель')
        tire_db_cols_map = {"Тип": "type", "Сезон": "season", "Модель": "model"}
        actual_tire_data_to_insert = {
            db_col: tire_data_from_dialog[display_col]
            for display_col, db_col in tire_db_cols_map.items()
            if display_col in tire_data_from_dialog
        }
        actual_tire_data_to_insert['idproduct'] = idproduct

        cols = ", ".join([f"`{col}`" for col in actual_tire_data_to_insert.keys()])
        placeholders = ", ".join(["%s"] * len(actual_tire_data_to_insert))
        query_tire = f"INSERT INTO `tires` ({cols}) VALUES ({placeholders})"
        return self._execute_query(query_tire, list(actual_tire_data_to_insert.values()), fetch=False)

    def update_tire_and_product_price(self, idtire, idproduct, tire_data_from_dialog, new_product_price):
        """ Обновляет шину и цену связанного продукта. """
        if not self._update_product_price(idproduct, new_product_price):
            print(f"MODEL: Не удалось обновить цену для продукта ID {idproduct}")
            # Решить, продолжать ли обновление шины

        tire_db_cols_map = {"Тип": "type", "Сезон": "season", "Модель": "model"}
        actual_tire_data_to_update = {
            db_col: tire_data_from_dialog[display_col]
            for display_col, db_col in tire_db_cols_map.items()
            if display_col in tire_data_from_dialog
        }
        if not actual_tire_data_to_update: return True  # Обновлялась только цена

        set_clause = ", ".join([f"`{col}` = %s" for col in actual_tire_data_to_update.keys()])
        query_tire = f"UPDATE `tires` SET {set_clause} WHERE `idtires` = %s"
        params_tire = list(actual_tire_data_to_update.values()) + [idtire]
        return self._execute_query(query_tire, params_tire, fetch=False)

    def insert_record(self, table_name, data_dict_from_dialog, table_configs):
        """ Вставляет запись. Использует table_configs для преобразования ключей. """
        if table_name == "tires":
            product_price = data_dict_from_dialog.pop("Цена_Продукта", 0)  # Ключ из editable_fields
            return self.insert_tire_with_product(data_dict_from_dialog, product_price)

        config = table_configs.get(table_name)
        if not config or "db_columns_map" not in config:
            print(f"MODEL: Конфигурация для вставки в таблицу {table_name} не найдена или неполна.")
            return False

        db_columns_map = config["db_columns_map"]
        actual_data_to_insert = {}
        for display_key, db_key in db_columns_map.items():
            if display_key in data_dict_from_dialog:
                actual_data_to_insert[db_key] = data_dict_from_dialog[display_key]
            # Для FK, если они передаются напрямую с именем столбца БД (например, idclient из диалога)
            elif db_key in data_dict_from_dialog and db_key in ["idclient", "idemployee"]:
                actual_data_to_insert[db_key] = data_dict_from_dialog[db_key]

        if not actual_data_to_insert: print("MODEL: Нет данных для вставки."); return False
        cols = ", ".join([f"`{col}`" for col in actual_data_to_insert.keys()])
        placeholders = ", ".join(["%s"] * len(actual_data_to_insert))
        query = f"INSERT INTO `{table_name}` ({cols}) VALUES ({placeholders})"
        return self._execute_query(query, list(actual_data_to_insert.values()), fetch=False)

    def update_record(self, table_name, record_id, data_dict_from_dialog, table_configs):
        """ Обновляет запись. Использует table_configs. """
        if table_name == "tires":
            # data_dict_from_dialog содержит 'idproduct', 'Цена_Продукта' и поля шины
            idproduct = data_dict_from_dialog.pop("idproduct")  # Ключ из initial_value_keys
            new_product_price = data_dict_from_dialog.pop("Цена_Продукта")  # Ключ из editable_fields
            return self.update_tire_and_product_price(record_id, idproduct, data_dict_from_dialog, new_product_price)

        config = table_configs.get(table_name)
        if not config or "db_columns_map" not in config or "pk_db_col" not in config:
            print(f"MODEL: Конфигурация для обновления таблицы {table_name} не найдена или неполна.")
            return False

        db_columns_map = config["db_columns_map"]
        pk_db_col = config["pk_db_col"]
        actual_data_to_update = {}
        for display_key, db_key in db_columns_map.items():
            if display_key in data_dict_from_dialog:
                actual_data_to_update[db_key] = data_dict_from_dialog[display_key]
            elif db_key in data_dict_from_dialog and db_key in ["idclient", "idemployee"]:
                actual_data_to_update[db_key] = data_dict_from_dialog[db_key]

        if not actual_data_to_update: print("MODEL: Нет данных для обновления."); return False
        set_clause = ", ".join([f"`{col}` = %s" for col in actual_data_to_update.keys()])
        query = f"UPDATE `{table_name}` SET {set_clause} WHERE `{pk_db_col}` = %s"
        params = list(actual_data_to_update.values()) + [record_id]
        return self._execute_query(query, params, fetch=False)

    def delete_record(self, table_name, record_id, table_configs):
        """ Удаляет запись. Для 'tires' также удаляет связанный 'product'. """
        config = table_configs.get(table_name)
        if not config or "pk_db_col" not in config:
            print(f"MODEL: Конфигурация для удаления из таблицы {table_name} не найдена.")
            return False
        pk_db_col = config["pk_db_col"]
        idproduct_to_delete = None

        if table_name == "tires":
            try:  # Получаем idproduct для удаления связанного продукта
                self.cursor.execute(f"SELECT idproduct FROM tires WHERE {pk_db_col} = %s", (record_id,))
                result = self.cursor.fetchone()
                if result: idproduct_to_delete = result['idproduct']
            except mysql.connector.Error as err:
                print(f"MODEL: Ошибка при получении idproduct для удаления шины: {err}");
                return False

        # Удаляем основную запись
        if not self._execute_query(f"DELETE FROM `{table_name}` WHERE `{pk_db_col}` = %s", (record_id,), fetch=False):
            return False

        if table_name == "tires" and idproduct_to_delete:
            print(f"MODEL: Удаление связанного продукта ID: {idproduct_to_delete}")
            if not self._execute_query("DELETE FROM `product` WHERE `idproduct` = %s", (idproduct_to_delete,),
                                       fetch=False):
                print(f"MODEL: Внимание! Шина удалена, но связанный продукт ID:{idproduct_to_delete} не удален.")
        return True

    # --- Вспомогательные методы для выпадающих списков в диалогах ---
    def get_clients_for_dropdown(self):
        return self._execute_query("SELECT idclient, FIO FROM client ORDER BY FIO")

    def get_employees_for_dropdown(self):
        return self._execute_query("SELECT idemployee, FIO FROM employee ORDER BY FIO")

    # --- Методы для вызова SQL процедур и функций ---
    def call_get_order_information(self, order_id):
        """ Вызывает процедуру get_order_information. """
        try:
            self.cursor.execute("SELECT status FROM `order` WHERE idorder = %s", (order_id,))
            status_result = self.cursor.fetchone()
            if not status_result: return [{"Ошибка": f"Заказ с ID {order_id} не найден."}]
            if status_result['status'] == "Отменен": return [{"Статус_Заказа": status_result['status']}]

            self.cursor.callproc('get_order_information', [order_id])
            results = [item for res_set in self.cursor.stored_results() for item in res_set.fetchall()]
            return results if results else [{"Информация": f"Нет данных для заказа ID {order_id}."}]
        except mysql.connector.Error as err:
            return [{"Ошибка": f"SQL Proc (order_info): {err}"}]

    def call_get_sold_tires_count_in_period(self, date_start_str, date_end_str):
        """ Вызывает функцию GetSoldTiresCountInPeriod. """
        try:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%d').date()
            date_end = datetime.strptime(date_end_str, '%Y-%m-%d').date()
            self.cursor.execute("SELECT GetSoldTiresCountInPeriod(%s, %s) AS count", (date_start, date_end))
            result = self.cursor.fetchone()
            return result['count'] if result and result['count'] is not None else 0
        except ValueError:
            return "Ошибка: Неверный формат даты (ГГГГ-ММ-ДД)."
        except mysql.connector.Error as err:
            return f"Ошибка БД (sold_tires_count): {err}"

    def call_get_product_by_categories(self, category_type, min_sum, max_sum):
        """ Вызывает процедуру get_product_by_categories. """
        try:
            min_s, max_s = float(min_sum), float(max_sum)
            # процедура: (in type varchar(100), in max_sum float, in min_sum float)
            self.cursor.callproc('get_product_by_categories', [category_type, max_s, min_s])
            results = [item for res_set in self.cursor.stored_results() for item in res_set.fetchall()]
            return results if results else [{"Информация": f"Нет продуктов для '{category_type}' ({min_s}-{max_s})."}]
        except ValueError:
            return [{"Ошибка": "Суммы должны быть числами."}]
        except mysql.connector.Error as err:
            return [{"Ошибка": f"SQL Proc (product_by_cat): {err}"}]