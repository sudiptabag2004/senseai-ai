import queue
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import List, Tuple
from lib.config import sqlite_db_path
from lib.utils.logging import logger


def trace_callback(sql):
    # Record the start time and SQL
    logger.info(f"Executing operation: {sql}")


def get_new_db_connection():
    conn = sqlite3.connect(sqlite_db_path)

    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.set_trace_callback(trace_callback)

    return conn


def set_db_defaults():
    conn = sqlite3.connect(sqlite_db_path)

    current_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]

    if current_mode.lower() != "wal":
        settings = "PRAGMA journal_mode = WAL;"

        conn.executescript(settings)
        print("Defaults set.")
    else:
        print("Defaults already set.")


def execute_db_operation(
    operation,
    params=None,
    fetch_one=False,
    fetch_all=False,
    get_last_row_id=False,
):
    with get_new_db_connection() as conn:
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

            conn.commit()

            if get_last_row_id:
                return cursor.lastrowid

            return result
        except Exception as e:
            raise e


def execute_many_db_operation(operation, params_list):
    with get_new_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(operation, params_list)
            conn.commit()
        except Exception as e:
            raise e


def execute_multiple_db_operations(commands_and_params: List[Tuple[str, Tuple]]):
    """
    Execute multiple SQL commands under the same connection.
    Each command is a tuple of (sql_command, params).
    All commands are executed in a single transaction.
    """
    with get_new_db_connection() as conn:
        cursor = conn.cursor()
        try:
            for command, params in commands_and_params:
                cursor.execute(command, params)
            conn.commit()
        except Exception as e:
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
