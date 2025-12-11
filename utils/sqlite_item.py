from sqlite3 import Connection
from typing import Any, Dict
from sqlite import (
    select_items,
    update_items,
    insert_items,
    delete_items,
    create_connection,
    filter_items,
    get_random_row,
)

conn = None


class SQLiteItem:

    logging = True
    db_path: str = None
    _conn: Connection = None
    _column_names = []
    _table_name = None
    _filter_condition = None
    _token = None

    _conjunction_type = "AND"

    def __init__(
        self,
        table_values: list,
        column_names: list = None,
        logging: bool = False,
        db_path: str = None,
    ) -> None:
        self.table_name = self.__class__.__name__
        self.table_values = table_values
        self.column_names = column_names
        self.logging = logging
        self._filter_condition = None
        self.db_path = db_path if db_path else None

    @property
    def conjunction_type(self):
        return self._conjunction_type

    @conjunction_type.setter
    def conjunction_type(self, conjunction_type: str):
        self._conjunction_type = conjunction_type

    @property
    def table_name(self):
        return self._table_name

    @table_name.setter
    def table_name(self, table_name: str):
        self._table_name = table_name

    @property
    def column_names(self):
        return self._column_names

    @column_names.setter
    def column_names(self, column_names: list):
        self._column_names = (
            column_names if column_names else self.get_column_names_from_table()
        )

    @property
    def conn(self):
        if self._conn is None:
            global conn
            if conn is None:
                conn = create_connection(self.db_path)
            self._conn = conn

        return self._conn

    @property
    def filter_condition(self):
        return self._filter_condition

    @filter_condition.setter
    def filter_condition(self, new_filter_condition):
        self._filter_condition = new_filter_condition

    # sqlite operations

    def get_unique_object(self):
        sqlite_item = SQLiteItem(self.table_values, self.column_names)
        sqlite_keys = list(vars(sqlite_item).keys())

        dictionary: dict = vars(self)
        temp_dict = dictionary.copy()

        for key in dictionary:
            if key in sqlite_keys or key.startswith("_") or key.startswith("__"):
                temp_dict.pop(key)
        return temp_dict

    def get_default_attr_names(self):
        return [name for name in self.column_names if name != "id"]

    def get_column_names_from_table(self):
        return [v.split(" ")[0] for v in self.table_values]

    def get_object_values(self, attr_names: list = []):

        if not attr_names:
            attr_names = self.column_names

        return [getattr(self, name) for name in attr_names]

    def filter_by(self, query_params: list = None, conjunction_type: str = None):

        if query_params is None:
            query_params = self.column_names

        conjunction_type = (
            self.conjunction_type if conjunction_type is None else conjunction_type
        )

        items = filter_items(
            self.conn, self.table_name, query_params, self, conjunction_type
        )
        return items

    def select(self, filter_condition=None):

        condition = (
            self.filter_condition if filter_condition is None else filter_condition
        )

        items = select_items(
            self.conn,
            self.table_name,
            condition,
            type(self),
            column_names=self.column_names,
        )

        return items

    def select_first(self, filter_condition=None):
        items = self.select(filter_condition)
        return items[0] if len(items) > 0 else None

    def select_all(self):
        return select_items(
            self.conn, self.table_name, None, type(self), self.column_names
        )

    def insert(self):
        return insert_items(self.conn, self.table_name, [self], self.column_names)

    @classmethod
    def insert_all(cls, items: list):
        for item in items:
            if isinstance(item, SQLiteItem):
                item.insert()

    def upsert(self, filter_condition=None):
        if self.item_exists(filter_condition):
            id = self.update(filter_condition)
        else:
            id = self.insert()

        return id

    def update(self, filter_condition=None):
        condition = (
            self.filter_condition if filter_condition is None else filter_condition
        )

        return update_items(
            self.conn, self.table_name, [self], condition, self.column_names
        )

    def delete(self, filter_condition=None):

        condition = (
            self.filter_condition if filter_condition is None else filter_condition
        )
        return delete_items(self.conn, self.table_name, condition)

    def item_exists(self, filter_condition=None) -> bool:
        condition = (
            self.filter_condition if filter_condition is None else filter_condition
        )
        return self.select_first(condition) is not None

    def get_random_item(self):
        item = get_random_row(self.conn, self.table_name, type(self))
        return item[0] if len(item) > 0 else None

    def log(self, log_message: str = None):

        if self.logging and log_message:
            print(log_message)

    def as_dict(self, column_names: list = None) -> Dict[str, Any]:
        """Convert the model instance to a dictionary without leading underscores."""

        column_names = self.column_names if not column_names else column_names

        if isinstance(column_names, str):
            column_names = column_names.split(",")

        result = {}

        for column_name in column_names:
            # print("COLUMN", column_name)
            value = getattr(self, column_name)
            result[column_name] = value
            # print("VALUE", value)

        return result

    @classmethod
    def from_dict(cls, data: dict):
        """Initialize model from a dictionary, useful for API responses."""
        obj = cls.__new__(cls)

        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        return obj
