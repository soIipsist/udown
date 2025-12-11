import argparse
from datetime import datetime
from functools import lru_cache
from inspect import getmembers, signature
from itertools import zip_longest
import os
from pprint import PrettyPrinter
import sqlite3
from ast import literal_eval
import re
from urllib.parse import urlparse

pp = PrettyPrinter(depth=4)


def get_callable_args(func, args: dict = None) -> dict:
    """Given a function, return all of its arguments with default values included."""

    if not callable(func):
        raise ValueError("not a function")

    func_signature = signature(func)
    func_params = {param.name: param for param in func_signature.parameters.values()}

    func_dict = {}
    for key, param in func_params.items():
        if key != "self" and key != "kwargs" and key != "args":
            p = None if param.default == param.empty else param.default
            if args and args.get(key):
                p = args.get(key)
            func_dict.update({key: p})
    return func_dict


def get_date_format(date_string: str, date_formats=[]):
    """Returns date format of a given string."""

    if not date_formats:
        date_formats = [
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
        ]

    for date_format in date_formats:
        try:

            datetime.strptime(date_string, date_format)
            return date_format

        except ValueError:
            pass


def is_valid_url(url: str):
    """Check if a given string is a valid URL."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def is_valid_path(path, raise_error=True):
    if not os.path.exists(path):
        if raise_error:
            raise FileNotFoundError(path)
        return None
    return path


def create_connection(database_path: str):
    """
    Create a connection to an SQLite database.
    """
    try:
        conn = sqlite3.connect(database_path)
        return conn
    except sqlite3.Error as e:
        print("Error connecting to the database:", e)
        print("Database path: ", database_path)
        return None


def select_items(
    conn: sqlite3.Connection,
    table_name: str,
    filter_condition: str = None,
    mapped_object_type=None,
    column_names: list = [],
):
    """
    Retrieves a collection of items stored in the SQLite database.
    """
    query = f"SELECT * FROM {sanitize_values(table_name)[0]}"
    if filter_condition:
        filter_condition, params = get_filter_condition(filter_condition)

        query += f" WHERE {filter_condition}"
        results = execute_query(conn, query, params)
    else:
        results = execute_query(conn, query)

    return (
        results
        if not mapped_object_type
        else map_sqlite_results_to_objects(results, mapped_object_type, column_names)
    )


def view_items(
    conn: sqlite3.Connection,
    table_name: str,
    filter_condition: str = None,
    mapped_object_type=None,
    column_names: list = [],
):

    column_names = (
        get_column_names(conn.cursor(), table_name)
        if not column_names
        else column_names
    )

    items = select_items(
        conn, table_name, filter_condition, mapped_object_type, column_names
    )

    for item in items:
        item_dict = dict(zip(column_names, item))
        pp.pprint(item_dict)
        print("")


def sanitize_filter_condition(filter_condition: str):
    """
    Sanitizes filter condition of type id = '1'. Returns the filter condition keys and a tuple of sanitized parameters.
    """

    if not isinstance(filter_condition, str):
        raise ValueError("filter_condition must be of type str.")

    filter_condition_keys = []
    sanitized_params = []

    conditions = filter_condition.split("AND")

    for condition in conditions:
        key, value = condition.split("=")

        key = key.strip()
        value = value.strip()
        filter_condition_keys.append(key)
        sanitized_params.append(value)

    return filter_condition_keys, tuple(sanitized_params)


def sanitize_values(values: list):
    """
    Sanitize values by removing non-word characters.
    """
    expression = r"\W+"

    if not isinstance(values, list):
        values = [values]

    for i, value in enumerate(values):
        if (
            not get_date_format(value)
            and not is_valid_url(value)
            and not is_valid_path(value, False)
        ):
            values[i] = re.sub(expression, "", value)
    return values


def get_column_names(cursor: sqlite3.Cursor, table_name: str):
    """
    Returns the columns of a table.
    """

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [col[1] for col in columns]


def insert_items(
    conn: sqlite3.Connection, table_name: str, objects: list, column_names: list = None
):
    """
    Insert data into an SQLite table.
    """
    if column_names and not isinstance(column_names, list):
        raise ValueError("'column_names' must be of type list.")

    if not isinstance(objects, list):
        raise ValueError("'objects' must be a list.")

    try:
        column_names = (
            get_column_names(conn.cursor(), table_name)
            if column_names is None
            else column_names
        )
        placeholders = ", ".join(["?"] * len(column_names))
        columns = ", ".join(column_names)

        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        last_row_id = None
        for obj in objects:
            values = get_object_values(obj, column_names)
            cursor, results = execute_query(conn, query, values, return_cursor=True)
            if cursor:
                last_row_id = cursor.lastrowid if cursor.lastrowid else last_row_id

        return last_row_id
    except sqlite3.Error as e:
        print("Error inserting data:", e)


def update_items(
    conn: sqlite3.Connection,
    table_name: str,
    objects: list,
    filter_condition: str,
    column_names: list = None,
):
    """Update any given SQL object based on a filter condition."""

    if column_names and not isinstance(column_names, list):
        raise ValueError("'column_names' must be of type list.")

    if not isinstance(objects, list):
        raise ValueError("'objects' must be a list.")

    try:

        column_names = (
            get_column_names(conn.cursor(), table_name)
            if column_names is None
            else column_names
        )
        set_clause = ", ".join([f"{column} = ?" for column in column_names])
        filter_condition, params = get_filter_condition(filter_condition)

        query = f"UPDATE {table_name} SET {set_clause} WHERE {filter_condition}"

        for obj in objects:
            update_values = get_object_values(obj, column_names)
            update_values.extend(params)
            cursor, results = execute_query(
                conn, query, update_values, return_cursor=True
            )
            last_row_id = None
            if cursor:
                last_row_id = cursor.lastrowid if cursor.lastrowid else last_row_id

        return last_row_id
    except sqlite3.Error as e:
        print("Error updating data: ", e)
        return -1


def get_object_values(obj, column_names: list):
    """Given a list of column names, returns the respective values for an object."""

    def normalize(value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        return str(value)

    results = []

    for name in column_names:

        result = normalize(
            obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
        )
        results.append(result)
        # print("RES", result, obj, name)
    return results


def get_last_inserted_row_id(conn: sqlite3.Connection, table_name: str):
    """Returns last inserted row id."""

    query = f"SELECT id FROM {table_name} ORDER BY id DESC LIMIT 1"
    result = execute_query(conn, query)
    return result[0][0] if len(result) > 0 else 0


def filter_items(
    conn: sqlite3.Connection,
    table_name: str,
    query_params: list,
    object: object,
    conjunction_type: bool = "AND",
):
    """Given an object and a list of attributes, return filtered items."""

    filter_condition = []

    for param in query_params:

        if hasattr(object, param):
            value = getattr(object, param)
            if value:
                if isinstance(value, str):
                    value_str = f"'%{value}%'"
                    filter_condition.append(f"{param} LIKE {value_str}")
                else:
                    filter_condition.append(f"{param} = {value}")

    filter_condition = f" {conjunction_type} ".join(filter_condition)
    # print("FILTER CONDITION", filter_condition)
    items = select_items(conn, table_name, filter_condition, type(object), query_params)
    return items


@lru_cache(maxsize=None)
def get_cached_column_names(cls):
    return list(get_callable_args(cls.__init__).keys())


def map_sqlite_results_to_objects(
    sqlite_results: list, object_type, column_names: list = []
):
    """Maps SQLite query results to a list of objects"""

    if not column_names:
        # return [object_type(*row) for row in sqlite_results]
        column_names = get_cached_column_names(object_type)

    objects = []

    # Identify columns that may require `literal_eval`
    eval_needed = [name for name in column_names if isinstance(name, str)]

    for result in sqlite_results:
        o = object_type()

        for value, column_name in zip_longest(result, column_names):
            # Only evaluate if this column is in the pre-determined list

            if (
                column_name in eval_needed
                and isinstance(value, str)
                and (
                    value.startswith("[")
                    and value.endswith("]")
                    or value.startswith("{")
                    and value.endswith("}")
                )
            ):
                value = literal_eval(value)

            if column_name is not None and hasattr(o, column_name):
                setattr(o, column_name, value)

            # print("LVALUE", column_name, value)

        objects.append(o)

    return objects


def delete_items(
    conn: sqlite3.Connection, table_name: str, filter_condition: str = "id = ?"
):
    """
    Deletes existing records from table.
    """
    table_name = sanitize_values(table_name)[0]
    query = f"DELETE FROM {table_name}"

    if filter_condition == "all" or filter_condition is None:
        return execute_query(conn, query)
    else:
        filter_condition, params = get_filter_condition(filter_condition)
        query += f" WHERE {filter_condition}"
        return execute_query(conn, query, params)


def delete_items_with_dialog(
    conn: sqlite3.Connection, table_name: str, filter_condition: str = "id = ?"
):
    a = input(f"Are you sure you want to delete records from '{table_name}'? (y/N): ")

    if a.lower() == "y":
        delete_items(conn, table_name, filter_condition)


def execute_query(
    conn: sqlite3.Connection, query: str, parameters: list = None, return_cursor=False
):
    """
    Execute an SQL query on the SQLite database.
    """

    results = []
    cursor = None

    try:
        cursor = conn.cursor()
        if parameters:
            # print(query, parameters)
            cursor.execute(query, parameters)
        else:
            # print(query)
            cursor.execute(query)
        results = cursor.fetchall()
        conn.commit()

    except sqlite3.Error as e:
        print(f"Error executing query: {e} \n {query}")

    if return_cursor:
        return cursor, results

    return results


def create_table(conn: sqlite3.Connection, table_name: str, table_values: list):
    """
    Create a new SQLite table.
    """
    table_name = sanitize_values(table_name)[0]

    placeholders = ", ".join(table_values)
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({placeholders})"
    execute_query(conn, query)

    return table_name


def close_connection(conn: sqlite3.Connection):
    """
    Close the SQLite database connection.
    """

    if conn:
        conn.close()


def get_random_row(
    conn: sqlite3.Connection, table_name: str, mapped_object_type: type = None
):
    """
    Returns a random row in the SQLite database, if it exists.
    """

    table_name = sanitize_values(table_name)[0]
    results = execute_query(
        conn, "SELECT * FROM {} ORDER BY RANDOM() LIMIT 1".format(table_name)
    )
    return (
        results
        if mapped_object_type is None
        else map_sqlite_results_to_objects(results, mapped_object_type)
    )


def is_valid_quote_string(quoted_string: str) -> bool:
    """
    Check if the quoted string contains any dangerous patterns.
    """
    stripped_string = quoted_string.strip("'")

    # Define patterns to be considered safe for quoted strings
    safe_patterns = [
        r"^[a-zA-Z0-9\s\(\)\-_\.\,\;\/\:\+]*$",
        r"^[a-zA-Z0-9\s\(\)\-_\.\,\;\/\:\+\'\"\=\*\&\!\?\#\$]*$",
    ]

    for pattern in safe_patterns:
        if re.match(pattern, stripped_string):
            return True

    return False


def get_filter_condition(filter_condition: str, default_params: list = None):
    """
    Sanitizes filter condition of type id = '1'. Returns the filter condition with placeholders included and
    a tuple of sanitized parameters.
    """

    if not isinstance(filter_condition, str):
        raise ValueError("filter_condition must be of type str.")

    filter_condition_keys = []
    sanitized_params = []
    keywords = []

    pattern = r"(\s+AND\s+|\s+OR\s+|\s+NOT\s+)"
    parts = re.split(pattern, filter_condition)

    comparison_operators = ["!=", "<>", ">=", "<=", ">", "<", "=", "LIKE"]

    # Check for SQL injection patterns
    q_pattern = r"(--|;|\/\*|\*\/|\bEXEC\b|\bUNION\b|\bSUBSTRING\b|\bBENCHMARK\b|\bCONCAT\b|\bCHAR\b|\bSLEEP\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b)"
    q_pattern_found = False
    sql_injection_patterns = [
        q_pattern,
        r"(\bOR\b\s+\d+\s*=\s*\d+)",
        r"(\bOR\b\s*true\b)",
        r"(\bAND\b\s*false\b)",
        r"(\bOR\b\s*1\s*=\s*1)",
        r"(\bOR\b\s*'[^']+'\s*=\s*'[^']+')",
    ]

    for pattern in sql_injection_patterns:
        if re.search(pattern, filter_condition, re.IGNORECASE):
            if pattern == q_pattern:
                q_pattern_found = True
                continue
            raise ValueError("Potential SQL injection detected.", pattern)

    # Process the split parts
    conditions = []
    for part in parts:
        part = part.strip()
        if part in ("AND", "OR", "NOT"):
            keywords.append(part)
        else:
            for operator in comparison_operators:
                if operator in part:

                    key, value = re.split(
                        r"\s*" + re.escape(operator) + r"\s*", part, maxsplit=1
                    )
                    key = key.strip()

                    if q_pattern_found:
                        if (
                            value.startswith("'")
                            and value.endswith("'")
                            and is_valid_quote_string(value)
                        ):
                            pass
                        else:
                            raise ValueError(
                                "Potential SQL injection detected.",
                                is_valid_quote_string(value),
                                value.startswith("'"),
                            )

                    value = value.strip().strip(
                        "'"
                    )  # Assuming values are enclosed in single quotes

                    filter_condition_keys.append(key)
                    sanitized_params.append(value)
                    conditions.append(f"{key} {operator} ?")
                    break
            else:
                raise ValueError(f"Unsupported condition format: {part}")

    # Construct the final filter condition with placeholders
    final_filter_condition = conditions[0]

    if default_params:
        default_idx = 0
        for idx, param in enumerate(sanitized_params):
            if param == "?":
                sanitized_params[idx] = default_params[default_idx]
                default_idx += 1

    for i in range(len(keywords)):
        final_filter_condition += f" {keywords[i]} {conditions[i + 1]}"

    return (
        final_filter_condition,
        tuple(sanitized_params),
    )


def parse_kv(arg: str) -> dict:
    try:
        return dict(pair.split("=", 1) for pair in arg.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(
            "Object must be in key=value,key2=value2 format"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--database_path",
        type=str,
        default=os.environ.get("SQLITE_DB", "downloads.db"),
    )
    parser.add_argument(
        "-a",
        "--action",
        type=str,
        choices=["select", "delete", "insert", "delete_all"],
        default="select",
    )
    parser.add_argument("-c", "--column_names", nargs="?", default=None)
    parser.add_argument("-f", "--filter_condition", type=str, default=None)
    parser.add_argument("-o", "--object", default=None, type=parse_kv)
    parser.add_argument(
        "table_name",
        type=str,
        default=os.environ.get("SQLITE_TABLE", "downloads"),
        nargs="?",
    )

    args = parser.parse_args()

    # if not os.path.exists(args.database_path):
    #     raise FileNotFoundError("Database path does not exist.")

    conn = create_connection(args.database_path)

    action_map = {
        "select": lambda: view_items(
            conn, args.table_name, args.filter_condition, None, args.column_names
        ),
        "insert": lambda: insert_items(
            conn, args.table_name, [args.object], args.column_names
        ),
        "delete": lambda: delete_items_with_dialog(
            conn, args.table_name, args.filter_condition
        ),
    }

    output = action_map[args.action]()

    print(f"Executing {args.action}...")
    pp.pprint(output)
