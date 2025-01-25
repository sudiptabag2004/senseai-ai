import queue
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import List, Tuple
from lib.config import sqlite_db_path
from lib.utils.logging import logger


class DatabaseConnectionPool:
    def __init__(self, sqlite_db_path, max_connections=5):
        self.sqlite_db_path = sqlite_db_path
        self.max_connections = max_connections
        self.connections = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.Lock()

    def get_connection(self):
        try:
            conn = self.connections.get_nowait()
            logger.info("Connection retrieved from pool.")
            return conn
        except queue.Empty:
            with self.lock:
                if self.active_connections < self.max_connections:
                    self.active_connections += 1

                    conn = sqlite3.connect(self.sqlite_db_path, check_same_thread=False)

                    conn.set_trace_callback(self.trace_callback)

                    current_busy_timeout = conn.execute(
                        "PRAGMA busy_timeout;"
                    ).fetchone()[0]

                    conn.execute("PRAGMA synchronous=NORMAL;")

                    logger.info(
                        f"New connection created with busy timeout: {current_busy_timeout}"
                    )

                    return conn

            conn = self.connections.get()
            logger.info("Connection retrieved from pool after waiting.")
            return conn

    def return_connection(self, connection):
        if connection:
            try:
                self.connections.put_nowait(connection)
                logger.info("Connection returned to pool.")
            except queue.Full:
                connection.close()
                with self.lock:
                    self.active_connections -= 1
                logger.info("Connection closed due to full pool.")

    def trace_callback(self, sql):
        # Record the start time and SQL
        logger.info(f"Executing operation: {sql}")
        DatabaseConnectionPool.current_sql = sql
        DatabaseConnectionPool.start_time = time.time()

    def profile_callback(self):
        print("here")
        # Calculate duration and log if exceeds threshold
        end_time = time.time()
        duration = end_time - DatabaseConnectionPool.start_time
        # if duration > 0.005:  # 5ms threshold
        logger.error(
            f"Long-running query ({duration:.3f}s): {DatabaseConnectionPool.current_sql}"
        )

    # Initialize class variables
    current_sql = ""
    start_time = 0


def trace_callback(sql):
    # Record the start time and SQL
    logger.info(f"Executing operation: {sql}")


def get_new_db_connection():
    conn = sqlite3.connect(sqlite_db_path)

    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.set_trace_callback(trace_callback)

    return conn


global_db_pool = DatabaseConnectionPool(
    sqlite_db_path=sqlite_db_path, max_connections=5
)


@contextmanager
# def get_shared_db_connection():
#     # TODO: reverting the db_pool implementation here is not correct. a new pool is being used on every call instead of using one shared pool
#     # if we create one shared pool, we get an SQLite programming error: SQLite objects created in a thread can only be used in that same thread.
#     # We can disable this check but then, we will need to handle race conditions ourselves. Reading should be fine but insertion, update, delete # needs to happen with locks in place, a single writer queue for SQLite.
#     # For our use case, since we have a lot of writes that are going to happen, a single write queue might be a major block. Might be better
#     # to shift to postgres DB

#     # connection = None
#     # try:
#     #     connection = get_new_db_connection()
#     #     yield connection
#     # finally:
#     #     if connection:
#     #         connection.close()

#     connection = None
#     try:
#         connection = global_db_pool.get_connection()
#         yield connection
#     finally:
#         if connection:
#             global_db_pool.return_connection(connection)


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
