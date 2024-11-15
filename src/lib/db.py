import os
from os.path import exists
import sqlite3
from typing import List, Any, Tuple, Dict
from datetime import datetime, timezone, timedelta
import pandas as pd
from lib.config import (
    sqlite_db_path,
    chat_history_table_name,
    tasks_table_name,
    tests_table_name,
    cohorts_table_name,
    groups_table_name,
    user_groups_table_name,
    group_role_learner,
    group_role_mentor,
    milestones_table_name,
    users_table_name,
    badges_table_name,
    cv_review_usage_table_name,
)
from models import LeaderboardViewType
from lib.utils import get_date_from_str, generate_random_color, convert_utc_to_ist
import json


def create_tests_table(cursor):
    cursor.execute(
        f"""
            CREATE TABLE IF NOT EXISTS {tests_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                input TEXT NOT NULL,  -- This will store a JSON-encoded list of strings
                output TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id)
            )
            """
    )


def create_users_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {users_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                first_name TEXT,
                middle_name TEXT,
                last_name TEXT,
                default_dp_color TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
    )


def create_badges_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {badges_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                value TEXT NOT NULL,
                type TEXT NOT NULL,
                image_path TEXT NOT NULL,
                bg_color TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
    )


def create_cohort_tables(cursor):
    # Create a table to store cohorts
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {cohorts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )"""
    )

    # Create a table to store groups
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {groups_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id)
            )"""
    )

    # Create a table to store user_groups
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {user_groups_table_name} (
                user_id TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                learner_id TEXT,
                FOREIGN KEY (group_id) REFERENCES {groups_table_name}(id)
            )"""
    )


def create_milestones_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {milestones_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT
            )"""
    )


def create_tasks_table(cursor):
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
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    milestone_id INTEGER REFERENCES {milestones_table_name}(id)
                )"""
    )


def create_chat_history_table(cursor):
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


def create_cv_review_usage_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {cv_review_usage_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ai_review TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
    )


def check_table_exists(table_name: str, cursor):
    cursor.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    table_exists = cursor.fetchone()

    return table_exists is not None


def get_db_connection():
    # print(sqlite_db_path)
    return sqlite3.connect(sqlite_db_path)


def init_db():
    # Ensure the database folder exists
    db_folder = os.path.dirname(sqlite_db_path)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    conn = get_db_connection()
    cursor = conn.cursor()

    if exists(sqlite_db_path):
        if not check_table_exists(milestones_table_name, cursor):
            create_milestones_table(cursor)
            conn.commit()

        if not check_table_exists(users_table_name, cursor):
            create_users_table(cursor)
            conn.commit()

        if not check_table_exists(badges_table_name, cursor):
            create_badges_table(cursor)
            conn.commit()

        if not check_table_exists(cohorts_table_name, cursor):
            create_cohort_tables(cursor)
            conn.commit()

        if not check_table_exists(tasks_table_name, cursor):
            create_tasks_table(cursor)
            conn.commit()

        if not check_table_exists(tests_table_name, cursor):
            create_tests_table(cursor)
            conn.commit()

        if not check_table_exists(chat_history_table_name, cursor):
            create_chat_history_table(cursor)
            conn.commit()

        if not check_table_exists(cv_review_usage_table_name, cursor):
            create_cv_review_usage_table(cursor)
            conn.commit()

        conn.close()
        return

    try:
        create_milestones_table(cursor)

        create_users_table(cursor)

        create_badges_table(cursor)

        # Create a table to store tasks
        create_tasks_table(cursor)

        # Create a table to store chat history
        create_chat_history_table(cursor)

        # Create a table to store cv review usage
        create_cv_review_usage_table(cursor)

        # Create a table to store tests
        create_tests_table(cursor)

        create_cohort_tables(cursor)

        # Commit the changes and close the connection
        conn.commit()

    except Exception as exception:
        # delete db
        conn.close()
        os.remove(sqlite_db_path)
        raise exception

    finally:
        conn.close()


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
    milestone_id: int,
):
    tags_str = serialise_list_to_str(tags)
    coding_language_str = serialise_list_to_str(coding_languages)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        INSERT INTO {tasks_table_name} (name, description, answer, tags, type, coding_language, generation_model, verified, milestone_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                milestone_id,
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
                (
                    task_id,
                    json.dumps(test["input"]),
                    test["output"],
                    test.get("description", None),
                ),
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
        {"input": json.loads(row[0]), "output": row[1], "description": row[2]}
        for row in test_rows
    ]


def get_all_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT t.id, t.name, t.description, t.answer, t.tags, t.type, t.coding_language, t.generation_model, t.verified, t.timestamp, m.id as milestone_id, m.name as milestone_name
    FROM {tasks_table_name} t
    LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
    ORDER BY t.timestamp ASC
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
                "generation_model": row[7],
                "verified": bool(row[8]),
                "timestamp": row[9],
                "milestone_id": row[10],
                "milestone_name": row[11],
                "tests": tests,
            }
        )

    conn.close()

    return tasks_dicts


def get_all_verified_tasks(milestone_id: int):
    tasks = get_all_tasks()
    verified_tasks = [task for task in tasks if task["verified"]]
    if milestone_id:
        return [task for task in verified_tasks if task["milestone_id"] == milestone_id]
    return verified_tasks


def get_task_by_id(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT t.id, t.name, t.description, t.answer, t.tags, t.type, t.coding_language, t.generation_model, t.verified, t.timestamp, m.name as milestone_name
    FROM {tasks_table_name} t
    LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
    WHERE t.id = ?
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
        "generation_model": task[7],
        "verified": bool(task[8]),
        "timestamp": task[9],
        "milestone": task[10],
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
    INNER JOIN {tasks_table_name} task ON message.task_id = task.id
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
    SELECT id, timestamp, user_id, task_id, role, content, is_solved, response_type FROM {chat_history_table_name} WHERE task_id = ? AND user_id = ?
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
            "response_type": row[7],
        }
        for row in chat_history
    ]
    return chat_history_dicts


def get_solved_tasks_for_user(
    user_id: str, view_type: LeaderboardViewType = LeaderboardViewType.ALL_TIME
):
    conn = get_db_connection()
    cursor = conn.cursor()

    if view_type == LeaderboardViewType.ALL_TIME:
        cursor.execute(
            f"""
        SELECT DISTINCT task_id FROM {chat_history_table_name} WHERE user_id = ? AND is_solved = 1
        """,
            (user_id,),
        )
    else:
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        if view_type == LeaderboardViewType.WEEKLY:
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MONTHLY
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        cursor.execute(
            f"""
        WITH FirstSolved AS (
            SELECT task_id, MIN(datetime(timestamp, '+5 hours', '+30 minutes')) as first_solved_time
            FROM {chat_history_table_name}
            WHERE user_id = ? AND is_solved = 1
            GROUP BY task_id
        )
        SELECT DISTINCT task_id 
        FROM FirstSolved
        WHERE first_solved_time >= ?
        """,
            (user_id, start_date),
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


def update_message_timestamp(message_id: int, new_timestamp: datetime):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    UPDATE {chat_history_table_name} SET timestamp = ? WHERE id = ?
    """,
        (new_timestamp, message_id),
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

    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
    current_streak = []

    user_usage_dates = [
        get_date_from_str(date_str, "IST") for date_str in user_usage_dates
    ]

    for i, date in enumerate(user_usage_dates):
        if i == 0 and (today - date).days > 1:
            # the user has not used the app yesterday or today, so the streak is broken
            break
        if i == 0 or (user_usage_dates[i - 1] - date).days == 1:
            current_streak.append(date)
        else:
            break

    return current_streak


def get_user_activity_last_n_days(user_id: str, n: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the user's interactions for the last n days, ordered by date
    cursor.execute(
        f"""
    SELECT DATE(datetime(timestamp, '+5 hours', '+30 minutes')), COUNT(*)
    FROM {chat_history_table_name}
    WHERE user_id = ? AND DATE(datetime(timestamp, '+5 hours', '+30 minutes')) >= DATE(datetime('now', '+5 hours', '+30 minutes'), '-{n} days')
    GROUP BY DATE(timestamp)
    ORDER BY DATE(timestamp)
    """,
        (user_id,),
    )

    activity_per_day = cursor.fetchall()
    conn.close()

    active_days = []

    for date, count in activity_per_day:
        if count > 0:
            active_days.append(datetime.strptime(date, "%Y-%m-%d"))

    return active_days


def get_user_streak(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the user's interactions, ordered by timestamp
    cursor.execute(
        f"""
    SELECT MAX(datetime(timestamp, '+5 hours', '+30 minutes')) as timestamp
    FROM {chat_history_table_name}
    WHERE user_id = ?
    GROUP BY DATE(datetime(timestamp, '+5 hours', '+30 minutes'))
    ORDER BY timestamp DESC
    """,
        (user_id,),
    )

    user_usage_dates = cursor.fetchall()
    conn.close()

    return get_user_streak_from_usage_dates(
        [date_str for date_str, in user_usage_dates]
    )


def get_streaks(view: LeaderboardViewType = LeaderboardViewType.ALL_TIME):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Build date filter based on duration
    date_filter = ""
    if view == LeaderboardViewType.WEEKLY:
        date_filter = "AND DATE(datetime(timestamp, '+5 hours', '+30 minutes')) > DATE('now', 'weekday 0', '-7 days')"
    elif view == LeaderboardViewType.MONTHLY:
        date_filter = "AND strftime('%Y-%m', datetime(timestamp, '+5 hours', '+30 minutes')) = strftime('%Y-%m', 'now')"

    # Get all user interactions, ordered by user and timestamp
    cursor.execute(
        f"""
    SELECT user_id, GROUP_CONCAT(timestamp) as timestamps
    FROM (
        SELECT user_id, MAX(datetime(timestamp, '+5 hours', '+30 minutes')) as timestamp
        FROM {chat_history_table_name}
        WHERE 1=1 {date_filter}
        GROUP BY user_id, DATE(datetime(timestamp, '+5 hours', '+30 minutes'))
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
                (
                    task_id,
                    json.dumps(test["input"]),
                    test["output"],
                    test.get("description", None),
                ),
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


def drop_users_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {users_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {users_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_all_cohort_info():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"""DELETE FROM {user_groups_table_name}""")
    cursor.execute(f"""DELETE FROM {groups_table_name}""")
    cursor.execute(f"""DELETE FROM {cohorts_table_name}""")

    conn.commit()
    conn.close()


def drop_cohorts_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE IF EXISTS {cohorts_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {groups_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {user_groups_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_cohort(name: str, df: pd.DataFrame):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create cohort
        cursor.execute(
            f"""
            INSERT INTO {cohorts_table_name} (name)
            VALUES (?)
            """,
            (name,),
        )
        cohort_id = cursor.lastrowid

        # Create groups and user_group entries
        for group_name, group_df in df.groupby("Group Name"):
            # Create group
            cursor.execute(
                f"""
                INSERT INTO {groups_table_name} (cohort_id, name)
                VALUES (?, ?)
                """,
                (cohort_id, group_name),
            )
            group_id = cursor.lastrowid

            # Create user_group entries for learners
            for _, row in group_df.iterrows():
                cursor.execute(
                    f"""
                    INSERT INTO {user_groups_table_name} (user_id, group_id, role, learner_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        row["Learner Email"],
                        group_id,
                        group_role_learner,
                        row["Learner ID"],
                    ),
                )

            # Create user_group entry for mentor
            mentor_email = group_df["Mentor Email"].iloc[0]
            cursor.execute(
                f"""
                INSERT INTO {user_groups_table_name} (user_id, group_id, role)
                VALUES (?, ?, ?)
                """,
                (
                    mentor_email,
                    group_id,
                    group_role_mentor,
                ),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def add_user_to_cohort_group(user_id: int, group_id: int, role: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {user_groups_table_name} (user_id, group_id, role) VALUES (?, ?, ?)",
        (user_id, group_id, role),
    )
    conn.commit()
    conn.close()


def get_all_cohorts():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT c.id, c.name,
                   COUNT(DISTINCT g.id) AS num_batches,
                   COUNT(DISTINCT CASE WHEN ug.role = '{group_role_learner}' THEN ug.user_id END) AS num_learners,
                   COUNT(DISTINCT CASE WHEN ug.role = '{group_role_mentor}' THEN ug.user_id END) AS num_mentors
            FROM {cohorts_table_name} c
            LEFT JOIN {groups_table_name} g ON c.id = g.cohort_id
            LEFT JOIN {user_groups_table_name} ug ON g.id = ug.group_id
            GROUP BY c.id, c.name
            ORDER BY c.id DESC
            """
        )

        cohorts = cursor.fetchall()

        cohorts_list = []
        for row in cohorts:
            cohorts_list.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "num_batches": row[2],
                    "num_learners": row[3],
                    "num_mentors": row[4],
                }
            )

        return cohorts_list
    except Exception as e:
        print(f"Error fetching cohorts: {e}")
        return []
    finally:
        conn.close()


def get_cohort_by_id(cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Fetch cohort details
        cursor.execute(
            f"""SELECT * FROM {cohorts_table_name} WHERE id = ?""", (cohort_id,)
        )
        cohort = cursor.fetchone()

        if not cohort:
            return None

        # Fetch groups and their members
        cursor.execute(
            f"""
            SELECT g.id, g.name,
                   GROUP_CONCAT(CASE WHEN ug.role = '{group_role_learner}' THEN ug.user_id END) AS learner_emails,
                   GROUP_CONCAT(CASE WHEN ug.role = '{group_role_learner}' THEN ug.learner_id END) AS learner_ids,
                   MAX(CASE WHEN ug.role = '{group_role_mentor}' THEN ug.user_id END) AS mentor_email
            FROM {groups_table_name} g
            LEFT JOIN {user_groups_table_name} ug ON g.id = ug.group_id
            WHERE g.cohort_id = ?
            GROUP BY g.id, g.name
        """,
            (cohort_id,),
        )

        groups = cursor.fetchall()

        cohort_data = {
            "id": cohort[0],
            "name": cohort[1],
            "groups": [
                {
                    "id": group[0],
                    "name": group[1],
                    "learner_emails": group[2].split(",") if group[2] else [],
                    "learner_ids": group[3].split(",") if group[3] else [],
                    "mentor_email": group[4],
                }
                for group in groups
            ],
        }

        return cohort_data
    except Exception as e:
        print(f"Error fetching cohort details: {e}")
        return None
    finally:
        conn.close()


def get_cohort_group_learners(group_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT * FROM {user_groups_table_name} WHERE group_id = ? AND role = 'learner'",
        (group_id),
    )
    learners = cursor.fetchall()

    return [learner[0] for learner in learners]


def get_all_milestones():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {milestones_table_name}")
    milestones = cursor.fetchall()

    conn.close()

    # Convert the fetched data into a list of dictionaries
    return [
        {"id": milestone[0], "name": milestone[1], "color": milestone[2]}
        for milestone in milestones
    ]


def insert_milestone(name: str, color: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {milestones_table_name} (name, color) VALUES (?, ?)",
        (name, color),
    )
    conn.commit()
    conn.close()


def update_milestone_color(milestone_id: int, color: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {milestones_table_name} SET color = ? WHERE id = ?",
        (color, milestone_id),
    )
    conn.commit()
    conn.close()


def set_colors_for_existing_milestones():
    all_milestones = get_all_milestones()

    for milestone in all_milestones:
        milestone_id = milestone["id"]
        color = generate_random_color()
        update_milestone_color(milestone_id, color)


def delete_milestone(milestone_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {milestones_table_name} WHERE id = ?", (milestone_id,))
    conn.commit()
    conn.close()


def get_all_milestone_progress(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
    SELECT 
        m.id AS milestone_id,
        m.name AS milestone_name,
        m.color AS milestone_color,
        COUNT(DISTINCT t.id) AS total_tasks,
        SUM(CASE WHEN task_solved.is_solved = 1 THEN 1 ELSE 0 END) AS completed_tasks,
        COUNT(DISTINCT t.id) - SUM(CASE WHEN task_solved.is_solved = 1 THEN 1 ELSE 0 END) AS incomplete_tasks
    FROM 
        {milestones_table_name} m
    LEFT JOIN 
        {tasks_table_name} t ON m.id = t.milestone_id
    LEFT JOIN (
        SELECT 
            task_id, 
            user_id, 
            MAX(CASE WHEN is_solved = 1 THEN 1 ELSE 0 END) AS is_solved
        FROM 
            {chat_history_table_name}
        WHERE 
            user_id = ?
        GROUP BY 
            task_id, user_id
    ) task_solved ON t.id = task_solved.task_id
    WHERE 
        t.verified = 1
    GROUP BY 
        m.id, m.name, m.color
    HAVING 
        COUNT(DISTINCT t.id) > 0
    ORDER BY 
        incomplete_tasks DESC
    """

    cursor.execute(query, (user_id,))
    results = cursor.fetchall()

    conn.close()

    return [
        {
            "milestone_id": row[0],
            "milestone_name": row[1],
            "milestone_color": row[2],
            "total_tasks": row[3],
            "completed_tasks": row[4],
        }
        for row in results
    ]


def upsert_user(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Use UPSERT command to insert or update the user record
    color = generate_random_color()
    cursor.execute(
        f"""
        INSERT INTO {users_table_name} (email, first_name, middle_name, last_name, default_dp_color)
        VALUES (?, '', '', '', ?)
        ON CONFLICT(email) DO NOTHING
    """,
        (email, color),
    )

    conn.commit()
    conn.close()

    return email


def update_user(
    user_id: str,
    first_name: str,
    middle_name: str,
    last_name: str,
    default_dp_color: str,
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {users_table_name} SET first_name = ?, middle_name = ?, last_name = ?, default_dp_color = ? WHERE id = ?",
        (first_name, middle_name, last_name, default_dp_color, user_id),
    )
    conn.commit()
    conn.close()


def convert_user_db_to_dict(user: Tuple) -> Dict:
    return {
        "id": user[0],
        "email": user[1],
        "first_name": user[2],
        "middle_name": user[3],
        "last_name": user[4],
        "default_dp_color": user[5],
        "created_at": user[6],
    }


def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {users_table_name}")
    users = cursor.fetchall()

    conn.close()

    return [convert_user_db_to_dict(user) for user in users]


def get_user_by_email(email: str) -> Dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {users_table_name} WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        return None

    return convert_user_db_to_dict(user)


def get_user_by_id(user_id: str) -> Dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {users_table_name} WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    return convert_user_db_to_dict(user)


def get_user_cohorts(user_id: str) -> List[Dict]:
    """Get all cohorts (and the groups in each cohort) that the user is a part of along with their role in each group"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all cohorts and groups the user is a member of
    cursor.execute(
        f"""
        SELECT c.id, c.name, g.id, g.name, ug.role 
        FROM {cohorts_table_name} c
        JOIN {groups_table_name} g ON g.cohort_id = c.id
        JOIN {user_groups_table_name} ug ON ug.group_id = g.id
        WHERE ug.user_id = ?
    """,
        (user_id,),
    )

    results = cursor.fetchall()
    conn.close()

    # Convert results into nested dict structure
    cohorts = {}
    for cohort_id, cohort_name, group_id, group_name, role in results:
        if cohort_id not in cohorts:
            cohorts[cohort_id] = {"id": cohort_id, "name": cohort_name, "groups": []}

        cohorts[cohort_id]["groups"].append(
            {"id": group_id, "name": group_name, "role": role}
        )

    return list(cohorts.values())


def seed_users_table_with_existing_users():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all unique user ids from chat history table
    cursor.execute(f"SELECT DISTINCT user_id FROM {chat_history_table_name}")
    existing_chat_user_emails = [row[0] for row in cursor.fetchall()]

    # Get all existing user emails from users table
    cursor.execute(f"SELECT email FROM {users_table_name}")
    existing_user_emails = set([row[0] for row in cursor.fetchall()])

    # Find user ids that are not in the users table
    new_user_ids = [
        user_id
        for user_id in existing_chat_user_emails
        if user_id not in existing_user_emails
    ]

    # Insert new users into the users table
    for user_id in new_user_ids:
        random_color = generate_random_color()
        cursor.execute(
            f"INSERT INTO {users_table_name} (email, first_name, middle_name, last_name, default_dp_color) VALUES (?, ?, ?, ?, ?)",
            (user_id, "", "", "", random_color),
        )

    conn.commit()
    conn.close()

    print(f"Added {len(new_user_ids)} new users to the users table.")


def create_badge_for_user(
    user_id: int, value: str, badge_type: str, image_path: str, bg_color: str
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {badges_table_name} (user_id, value, type, image_path, bg_color) VALUES (?, ?, ?, ?, ?)",
        (user_id, value, badge_type, image_path, bg_color),
    )

    cursor.execute("SELECT last_insert_rowid()")
    badge_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return badge_id


def update_badge(
    badge_id: int, value: str, badge_type: str, image_path: str, bg_color: str
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {badges_table_name} SET value = ?, type = ?, image_path = ?, bg_color = ? WHERE id = ?",
        (value, badge_type, image_path, bg_color, badge_id),
    )
    conn.commit()
    conn.close()


def convert_badge_db_to_dict(badge: Tuple):
    if badge is None:
        return None

    return {
        "id": badge[0],
        "user_id": badge[1],
        "value": badge[2],
        "type": badge[3],
        "image_path": badge[4],
        "bg_color": badge[5],
    }


def get_badge_by_id(badge_id: int) -> Dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {badges_table_name} WHERE id = ?", (badge_id,))
    badge = cursor.fetchone()

    return convert_badge_db_to_dict(badge)


def get_badges_by_user_id(user_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT * FROM {badges_table_name} WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    badges = cursor.fetchall()

    return [convert_badge_db_to_dict(badge) for badge in badges]


def get_badge_by_type_and_user_id(user_id: int, badge_type: str) -> Dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT * FROM {badges_table_name} WHERE user_id = ? AND type = ?",
        (user_id, badge_type),
    )
    badge = cursor.fetchone()

    return convert_badge_db_to_dict(badge)


def delete_badge_by_id(badge_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {badges_table_name} WHERE id = ?", (badge_id,))
    conn.commit()
    conn.close()


def clear_badges_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {badges_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def drop_badges_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {badges_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {badges_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def add_cv_review_usage(user_id: int, ai_review: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {cv_review_usage_table_name} (user_id, ai_review) VALUES (?, ?)",
        (user_id, ai_review),
    )
    conn.commit()
    conn.close()


def transform_cv_review_usage_to_dict(cv_review_usage: Tuple):
    return {
        "id": cv_review_usage[0],
        "user_id": cv_review_usage[1],
        "user_email": cv_review_usage[2],
        "ai_review": cv_review_usage[3],
        "created_at": convert_utc_to_ist(
            datetime.fromisoformat(cv_review_usage[4])
        ).isoformat(),
    }


def drop_cv_review_usage_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {cv_review_usage_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {cv_review_usage_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_cv_review_usage():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT cv.id, cv.user_id, u.email, cv.ai_review , cv.created_at
        FROM {cv_review_usage_table_name} cv
        JOIN users u ON cv.user_id = u.id
    """
    )
    all_cv_review_usage = cursor.fetchall()

    return [
        transform_cv_review_usage_to_dict(cv_review_usage)
        for cv_review_usage in all_cv_review_usage
    ]
