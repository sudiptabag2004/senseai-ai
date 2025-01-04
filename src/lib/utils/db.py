import queue
import sqlite3
from contextlib import contextmanager
from typing import List, Tuple
from lib.config import sqlite_db_path


class DatabaseConnectionPool:
    def __init__(self, sqlite_db_path, max_connections=5):
        # https://stackoverflow.com/questions/8753442/thinking-behind-decision-of-database-connection-pool-size
        self.sqlite_db_path = sqlite_db_path
        self.max_connections = max_connections
        self.connections = queue.Queue(maxsize=max_connections)
        self.active_connections = 0

    def get_connection(self):
        try:
            return self.connections.get_nowait()
        except queue.Empty:
            if self.active_connections < self.max_connections:
                self.active_connections += 1
                return sqlite3.connect(self.sqlite_db_path)
            return self.connections.get()

    def return_connection(self, connection):
        if connection:
            try:
                self.connections.put_nowait(connection)
            except queue.Full:
                connection.close()
                self.active_connections -= 1


@contextmanager
def get_shared_db_connection():
    connection_pool = DatabaseConnectionPool(sqlite_db_path=sqlite_db_path)

    connection = None
    try:
        connection = connection_pool.get_connection()
        yield connection
    finally:
        if connection:
            connection_pool.return_connection(connection)


def get_new_db_connection():
    return sqlite3.connect(sqlite_db_path)


def execute_db_operation(
    operation,
    params=None,
    fetch_one=False,
    fetch_all=False,
    commit=True,
    get_last_row_id=False,
):
    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(operation, params)
            else:
                cursor.execute(operation)

            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = None

            if commit:
                conn.commit()

            if get_last_row_id:
                return cursor.lastrowid

            return result
        except Exception as e:
            if commit:
                conn.rollback()
            raise e


def execute_many_db_operation(operation, params_list):
    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(operation, params_list)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e


def execute_multiple_db_operations(commands_and_params: List[Tuple[str, Tuple]]):
    """
    Execute multiple SQL commands under the same connection.
    Each command is a tuple of (sql_command, params).
    All commands are executed in a single transaction.
    """
    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            for command, params in commands_and_params:
                cursor.execute(command, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e


def check_table_exists(table_name: str, cursor):
    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    table_exists = cursor.fetchone()

    return table_exists is not None


def serialise_list_to_str(list_to_serialise: List[str]):
    if list_to_serialise:
        return ",".join(list_to_serialise)

    return None


def deserialise_list_from_str(str_to_deserialise: str):
    if str_to_deserialise:
        return str_to_deserialise.split(",")

    return []
