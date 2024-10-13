import os
from os.path import exists
import sqlite3
from typing import List, Any, Tuple, Dict
from datetime import datetime
from lib.config import (
    sqlite_db_path,
    chat_history_table_name,
    tasks_table_name,
    tests_table_name,
)
from lib.utils import get_date_from_str


def check_and_update_chat_history_table():
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    # check if a column exists in a table
    cursor.execute(f"PRAGMA table_info({chat_history_table_name})")
    columns = [column[1] for column in cursor.fetchall()]

    if "is_solved" not in columns:
        try:
            cursor.execute(
                f"ALTER TABLE {chat_history_table_name} ADD COLUMN is_solved BOOLEAN NOT NULL DEFAULT 0"
            )
            conn.commit()
        except sqlite3.OperationalError:
            # ignore the error
            pass

    if "response_type" not in columns:
        try:
            cursor.execute(
                f"ALTER TABLE {chat_history_table_name} ADD COLUMN response_type TEXT"
            )
            conn.commit()
        except sqlite3.OperationalError:
            # ignore the error
            pass

    conn.close()


def create_tests_table(cursor):
    cursor.execute(
        f"""
            CREATE TABLE IF NOT EXISTS {tests_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                input TEXT NOT NULL,
                output TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id)
            )
            """
    )


def check_and_update_tasks_table():
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    # check if a column exists in a table
    cursor.execute(f"PRAGMA table_info({tasks_table_name})")
    columns_info = cursor.fetchall()
    columns = [column[1] for column in columns_info]

    if "type" not in columns:
        try:
            cursor.execute(
                f"ALTER TABLE {tasks_table_name} ADD COLUMN type TEXT NOT NULL DEFAULT 'text'"
            )
            conn.commit()
        except sqlite3.OperationalError:
            # ignore the error
            pass

    if "show_code_preview" in columns:
        try:
            cursor.execute(
                f"ALTER TABLE {tasks_table_name} DROP COLUMN show_code_preview"
            )
            conn.commit()
        except sqlite3.OperationalError:
            # ignore the error
            pass

    if "coding_language" not in columns:
        try:
            cursor.execute(
                f"ALTER TABLE {tasks_table_name} ADD COLUMN coding_language TEXT"
            )
            conn.commit()
        except sqlite3.OperationalError:
            # ignore the error
            pass

    conn.close()


def init_db():
    # Ensure the database folder exists
    db_folder = os.path.dirname(sqlite_db_path)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    if exists(sqlite_db_path):
        # Check if the tests table exists
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tests_table_name}'"
        )
        table_exists = cursor.fetchone()

        if not table_exists:
            # Create the tests table if it doesn't exist
            create_tests_table(cursor)
            conn.commit()

        # Apply any necessary schema changes
        check_and_update_chat_history_table()
        check_and_update_tasks_table()

        conn.close()
        return

    try:
        # Create a table to store tasks
        cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {tasks_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    tags TEXT,  -- Stored as comma-separated values
                    type TEXT NOT NULL DEFAULT 'text',
                    coding_language TEXT,
                    generation_model TEXT NOT NULL,
                    verified BOOLEAN NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
        )

        # Create a table to store chat history
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {chat_history_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                task_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                is_solved BOOLEAN NOT NULL DEFAULT 0,
                response_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id)
            )
            """
        )

        # Create a table to store tests
        create_tests_table(cursor)

        # Commit the changes and close the connection
        conn.commit()

    except Exception as exception:
        # delete db
        conn.close()
        os.remove(sqlite_db_path)
        raise exception

    finally:
        conn.close()


# @st.cache_resource
def get_db_connection():
    # print(sqlite_db_path)
    return sqlite3.connect(sqlite_db_path)


def serialise_list_to_str(list_to_serialise: List[str]):
    if list_to_serialise:
        return ",".join(list_to_serialise)

    return None


def deserialise_list_from_str(str_to_deserialise: str):
    if str_to_deserialise:
        return str_to_deserialise.split(",")

    return []


def store_task(
    name: str,
    description: str,
    answer: str,
    tags: List[str],
    task_type: str,
    coding_languages: List[str],
    generation_model: str,
    verified: bool,
    tests: List[dict],
):
    tags_str = serialise_list_to_str(tags)
    coding_language_str = serialise_list_to_str(coding_languages)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        INSERT INTO {tasks_table_name} (name, description, answer, tags, type, coding_language, generation_model, verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                description,
                answer,
                tags_str,
                task_type,
                coding_language_str,
                generation_model,
                verified,
            ),
        )

        task_id = cursor.lastrowid

        # Insert test cases
        for test in tests:
            cursor.execute(
                f"""
                INSERT INTO {tests_table_name} (task_id, input, output, description)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, test["input"], test["output"], test.get("description", None)),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_task(
    task_id: int,
    name: str,
    description: str,
    answer: str,
    task_tags: List[str],
    task_type: str,
    coding_languages: List[str],
    generation_model: str,
    verified: bool,
):
    task_tags_str = serialise_list_to_str(task_tags)
    coding_language_str = serialise_list_to_str(coding_languages)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    UPDATE {tasks_table_name}
    SET name = ?, description = ?, answer = ?, tags = ?, type = ?, coding_language = ?, generation_model = ?, verified = ?
    WHERE id = ?
    """,
        (
            name,
            description,
            answer,
            task_tags_str,
            task_type,
            coding_language_str,
            generation_model,
            verified,
            task_id,
        ),
    )

    conn.commit()
    conn.close()


def update_column_for_task_ids(task_ids: List[int], column_name: Any, new_value: Any):
    if isinstance(new_value, list):
        new_value = ",".join(new_value)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    UPDATE {tasks_table_name}
    SET {column_name} = ?
    WHERE id IN ({','.join(map(str, task_ids))})
    """,
        (new_value,),
    )

    conn.commit()
    conn.close()


def return_test_rows_as_dict(test_rows: List[Tuple[str, str, str]]) -> List[Dict]:
    return [
        {"input": row[0], "output": row[1], "description": row[2]} for row in test_rows
    ]


def get_all_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT id, name, description, answer, tags, type, coding_language, generation_model, verified, timestamp FROM {tasks_table_name}
    ORDER BY timestamp ASC
    """
    )

    tasks = cursor.fetchall()

    tasks_dicts = []
    for row in tasks:
        task_id = row[0]

        # Fetch associated tests for each task
        cursor.execute(
            f"""
        SELECT input, output, description FROM {tests_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

        tests = return_test_rows_as_dict(cursor.fetchall())

        tasks_dicts.append(
            {
                "id": task_id,
                "name": row[1],
                "description": row[2],
                "answer": row[3],
                "tags": deserialise_list_from_str(row[4]),
                "type": row[5],
                "coding_language": deserialise_list_from_str(row[6]),
                "generation_model": row[-3],
                "verified": bool(row[-2]),
                "timestamp": row[-1],
                "tests": tests,
            }
        )

    conn.close()

    return tasks_dicts


def get_task_by_id(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT id, name, description, answer, tags, type, coding_language, generation_model, verified, timestamp FROM {tasks_table_name} WHERE id = ?
    """,
        (task_id,),
    )

    task = cursor.fetchone()

    if not task:
        conn.close()
        return None

    # Fetch associated tests
    cursor.execute(
        f"""
    SELECT input, output, description FROM {tests_table_name} WHERE task_id = ?
    """,
        (task_id,),
    )

    tests = return_test_rows_as_dict(cursor.fetchall())

    conn.close()

    return {
        "id": task[0],
        "name": task[1],
        "description": task[2],
        "answer": task[3],
        "tags": deserialise_list_from_str(task[4]),
        "type": task[5],
        "coding_language": deserialise_list_from_str(task[6]),
        "generation_model": task[-3],
        "verified": bool(task[-2]),
        "timestamp": task[-1],
        "tests": tests,
    }


def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete associated tests first
        cursor.execute(
            f"""
        DELETE FROM {tests_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

        # Then delete the task
        cursor.execute(
            f"""
        DELETE FROM {tasks_table_name} WHERE id = ?
        """,
            (task_id,),
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_tasks(task_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete associated tests first
        cursor.execute(
            f"""
        DELETE FROM {tests_table_name} WHERE task_id IN ({','.join(map(str, task_ids))})
        """
        )

        # Then delete the tasks
        cursor.execute(
            f"""
        DELETE FROM {tasks_table_name} WHERE id IN ({','.join(map(str, task_ids))})
        """
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_all_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    DELETE FROM {tasks_table_name}
    """
    )

    conn.commit()
    conn.close()


def store_message(
    user_id: str,
    task_id: int,
    role: str,
    content: str,
    is_solved: bool = False,
    response_type: str = None,
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    INSERT INTO {chat_history_table_name} (user_id, task_id, role, content, is_solved, response_type)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (user_id, task_id, role, content, is_solved, response_type),
    )

    # Get the ID of the newly inserted row
    new_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Fetch the newly inserted row
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT id, timestamp, user_id, task_id, role, content, is_solved, response_type
    FROM {chat_history_table_name}
    WHERE id = ?
    """,
        (new_id,),
    )

    new_row = cursor.fetchone()

    conn.close()

    # Return the newly inserted row as a dictionary
    return {
        "id": new_row[0],
        "timestamp": new_row[1],
        "user_id": new_row[2],
        "task_id": new_row[3],
        "role": new_row[4],
        "content": new_row[5],
        "is_solved": new_row[6],
        "response_type": new_row[7],
    }


def get_all_chat_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT message.id, message.timestamp, message.user_id, message.task_id, task.name AS task_name, message.role, message.content, message.is_solved, message.response_type 
    FROM {chat_history_table_name} message
    LEFT JOIN {tasks_table_name} task ON message.task_id = task.id
    ORDER BY message.timestamp ASC
    """
    )

    chat_history = cursor.fetchall()

    conn.close()

    chat_history_dicts = [
        {
            "id": row[0],
            "timestamp": row[1],
            "user_id": row[2],
            "task_id": row[3],
            "task_name": row[4],
            "role": row[5],
            "content": row[6],
            "is_solved": bool(row[7]),
            "response_type": row[8],
        }
        for row in chat_history
    ]

    return chat_history_dicts


def get_task_chat_history_for_user(task_id: int, user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT id, timestamp, user_id, task_id, role, content, is_solved FROM {chat_history_table_name} WHERE task_id = ? AND user_id = ?
    """,
        (task_id, user_id),
    )

    chat_history = cursor.fetchall()

    conn.close()

    chat_history_dicts = [
        {
            "id": row[0],
            "timestamp": row[1],
            "user_id": row[2],
            "task_id": row[3],
            "role": row[4],
            "content": row[5],
            "is_solved": bool(row[6]),
        }
        for row in chat_history
    ]
    return chat_history_dicts


def get_solved_tasks_for_user(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT task_id FROM {chat_history_table_name} WHERE user_id = ? AND is_solved = 1
    """,
        (user_id,),
    )

    return [task[0] for task in cursor.fetchall()]


def delete_message(message_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    DELETE FROM {chat_history_table_name} WHERE id = ?
    """,
        (message_id,),
    )

    conn.commit()
    conn.close()


def delete_user_chat_history_for_task(task_id: int, user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    DELETE FROM {chat_history_table_name} WHERE task_id = ? AND user_id = ?
    """,
        (task_id, user_id),
    )

    conn.commit()
    conn.close()


def delete_all_chat_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    DELETE FROM {chat_history_table_name}
    """
    )

    conn.commit()
    conn.close()


def get_user_streak_from_usage_dates(user_usage_dates: List[str]) -> int:
    if not user_usage_dates:
        return []

    today = datetime.now().date()
    current_streak = []

    user_usage_dates = [get_date_from_str(date_str) for date_str in user_usage_dates]

    for i, date in enumerate(user_usage_dates):
        if i == 0 and (today - date).days > 1:
            # the user has not used the app yesterday or today, so the streak is broken
            break
        if i == 0 or (user_usage_dates[i - 1] - date).days == 1:
            current_streak.append(date)
        else:
            break

    return current_streak


def get_user_streak(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the user's interactions, ordered by timestamp
    cursor.execute(
        f"""
    SELECT MAX(timestamp) as timestamp
    FROM {chat_history_table_name}
    WHERE user_id = ?
    GROUP BY DATE(timestamp)
    ORDER BY timestamp DESC
    """,
        (user_id,),
    )

    user_usage_dates = cursor.fetchall()
    conn.close()

    return get_user_streak_from_usage_dates(
        [date_str for date_str, in user_usage_dates]
    )


def get_streaks():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all user interactions, ordered by user and timestamp
    cursor.execute(
        f"""
    SELECT user_id, GROUP_CONCAT(timestamp) as timestamps
    FROM (
        SELECT user_id, MAX(timestamp) as timestamp
        FROM {chat_history_table_name}
        GROUP BY user_id, DATE(timestamp)
        ORDER BY user_id, timestamp DESC
    )
    GROUP BY user_id
    """
    )

    usage_per_user = cursor.fetchall()
    conn.close()

    streaks = {}

    for user_id, user_usage_dates_str in usage_per_user:
        user_usage_dates = user_usage_dates_str.split(",")
        streaks[user_id] = len(get_user_streak_from_usage_dates(user_usage_dates))

    return streaks


def update_tests_for_task(task_id: int, tests: List[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete existing tests for the task
        cursor.execute(
            f"""
            DELETE FROM {tests_table_name} WHERE task_id = ?
            """,
            (task_id,),
        )

        # Insert new tests
        for test in tests:
            cursor.execute(
                f"""
                INSERT INTO {tests_table_name} (task_id, input, output, description)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, test["input"], test["output"], test.get("description", None)),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_all_tests():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {tests_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def drop_tests_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE IF EXISTS {tests_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
