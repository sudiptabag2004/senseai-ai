import os
from os.path import exists
import json
from collections import defaultdict
import streamlit as st
import traceback
import itertools
import sqlite3
import uuid
from unidecode import unidecode
from typing import List, Any, Tuple, Dict, Literal
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
    user_cohorts_table_name,
    group_role_learner,
    group_role_mentor,
    milestones_table_name,
    tags_table_name,
    task_tags_table_name,
    users_table_name,
    badges_table_name,
    cv_review_usage_table_name,
    organizations_table_name,
    user_organizations_table_name,
    task_scoring_criteria_table_name,
    courses_table_name,
    course_cohorts_table_name,
    course_tasks_table_name,
    uncategorized_milestone_name,
    uncategorized_milestone_color,
)
from models import LeaderboardViewType
from lib.utils import (
    get_date_from_str,
    generate_random_color,
    convert_utc_to_ist,
    load_json,
)
from lib.url import slugify


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


def create_organizations_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {organizations_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                default_logo_color TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
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


def create_user_organizations_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {user_organizations_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                org_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, org_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
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
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
            )"""
    )

    # Create a table to store users in cohorts
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {user_cohorts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                cohort_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                UNIQUE(user_id, cohort_id),
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id),
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id)
            )"""
    )

    # Create a table to store groups
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {groups_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id INTEGER NOT NULL,
                name TEXT,
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id)
            )"""
    )

    # Create a table to store user groups
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {user_groups_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                UNIQUE(user_id, group_id),
                FOREIGN KEY (group_id) REFERENCES {groups_table_name}(id)
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id)
            )"""
    )


def create_course_tasks_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {course_tasks_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                ordering INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, course_id),
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id),
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id)
            )"""
    )


def create_milestones_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {milestones_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
            )"""
    )


def create_tag_tables(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {tags_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
            )"""
    )

    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {task_tags_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, tag_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )"""
    )


def create_courses_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {courses_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
            )"""
    )


def create_course_cohorts_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {course_cohorts_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                cohort_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(course_id, cohort_id),
                FOREIGN KEY (course_id) REFERENCES {courses_table_name}(id),
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id)
            )"""
    )


def create_tasks_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {tasks_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    answer TEXT,
                    type TEXT NOT NULL DEFAULT 'text',
                    coding_language TEXT,
                    generation_model TEXT NOT NULL,
                    verified BOOLEAN NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    milestone_id INTEGER,
                    org_id INTEGER NOT NULL,
                    response_type TEXT NOT NULL,
                    FOREIGN KEY (milestone_id) REFERENCES {milestones_table_name}(id),
                    FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
                )"""
    )


def create_task_scoring_criteria_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {task_scoring_criteria_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                min_score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id)
            )"""
    )


def create_chat_history_table(cursor):
    cursor.execute(
        f"""
                CREATE TABLE IF NOT EXISTS {chat_history_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_solved BOOLEAN NOT NULL DEFAULT 0,
                    response_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id)
                    FOREIGN KEY (user_id) REFERENCES {users_table_name}(id)
                )
                """
    )


def create_cv_review_usage_table(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {cv_review_usage_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
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
        if not check_table_exists(organizations_table_name, cursor):
            create_organizations_table(cursor)
            conn.commit()

        if not check_table_exists(users_table_name, cursor):
            create_users_table(cursor)
            conn.commit()

        if not check_table_exists(user_organizations_table_name, cursor):
            create_user_organizations_table(cursor)
            conn.commit()

        if not check_table_exists(cohorts_table_name, cursor):
            create_cohort_tables(cursor)
            conn.commit()

        if not check_table_exists(courses_table_name, cursor):
            create_courses_table(cursor)
            conn.commit()

        if not check_table_exists(course_cohorts_table_name, cursor):
            create_course_cohorts_table(cursor)
            conn.commit()

        if not check_table_exists(milestones_table_name, cursor):
            create_milestones_table(cursor)
            conn.commit()

        if not check_table_exists(tags_table_name, cursor):
            create_tag_tables(cursor)
            conn.commit()

        if not check_table_exists(badges_table_name, cursor):
            create_badges_table(cursor)
            conn.commit()

        if not check_table_exists(tasks_table_name, cursor):
            create_tasks_table(cursor)
            conn.commit()

        if not check_table_exists(task_scoring_criteria_table_name, cursor):
            create_task_scoring_criteria_table(cursor)
            conn.commit()

        if not check_table_exists(tests_table_name, cursor):
            create_tests_table(cursor)
            conn.commit()

        if not check_table_exists(chat_history_table_name, cursor):
            create_chat_history_table(cursor)
            conn.commit()

        if not check_table_exists(course_tasks_table_name, cursor):
            create_course_tasks_table(cursor)
            conn.commit()

        if not check_table_exists(cv_review_usage_table_name, cursor):
            create_cv_review_usage_table(cursor)
            conn.commit()

        conn.close()
        return

    try:
        create_organizations_table(cursor)

        create_users_table(cursor)

        create_user_organizations_table(cursor)

        create_milestones_table(cursor)

        create_tag_tables(cursor)

        create_cohort_tables(cursor)

        create_courses_table(cursor)

        create_course_cohorts_table(cursor)

        create_badges_table(cursor)

        create_tasks_table(cursor)

        create_task_scoring_criteria_table(cursor)

        create_chat_history_table(cursor)

        create_tests_table(cursor)

        create_course_tasks_table(cursor)

        create_cv_review_usage_table(cursor)

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
    tags: List[Dict],
    task_type: str,
    response_type: str,
    coding_languages: List[str],
    generation_model: str,
    verified: bool,
    tests: List[dict],
    milestone_id: int,
    org_id: int,
):
    coding_language_str = serialise_list_to_str(coding_languages)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        INSERT INTO {tasks_table_name} (name, description, answer, type, coding_language, generation_model, verified, milestone_id, org_id, response_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                description,
                answer,
                task_type,
                coding_language_str,
                generation_model,
                verified,
                milestone_id,
                org_id,
                response_type,
            ),
        )

        task_id = cursor.lastrowid

        # Insert tags for the task
        for tag in tags:
            cursor.execute(
                f"""
                INSERT INTO {task_tags_table_name} (task_id, tag_id)
                VALUES (?, ?)
                """,
                (task_id, tag["id"]),
            )

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

        return task_id
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
    task_type: str,
    response_type: str,
    coding_languages: List[str],
    generation_model: str,
    verified: bool,
):
    coding_language_str = serialise_list_to_str(coding_languages)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    UPDATE {tasks_table_name}
    SET name = ?, description = ?, answer = ?, type = ?, coding_language = ?, generation_model = ?, verified = ?, response_type = ?
    WHERE id = ?
    """,
        (
            name,
            description,
            answer,
            task_type,
            coding_language_str,
            generation_model,
            verified,
            response_type,
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


def convert_task_db_to_dict(task, tests):
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
        "milestone_id": task[10],
        "milestone_name": task[11],
        "org_id": task[12],
        "org_name": task[13],
        "response_type": task[14],
        "tests": tests,
    }


def get_all_tasks_for_org_or_course(org_id: int = None, course_id: int = None):
    if org_id is None and course_id is None:
        raise ValueError("Either org_id or course_id must be provided")
    if org_id is not None and course_id is not None:
        raise ValueError("Only one of org_id or course_id can be provided")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""
    SELECT t.id, t.name, t.description, t.answer,
        GROUP_CONCAT(tg.name) as tags,
        t.type, t.coding_language, t.generation_model, t.verified, t.timestamp, m.id as milestone_id, m.name as milestone_name, o.id, o.name as org_name,
        t.response_type
    FROM {tasks_table_name} t
    LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
    LEFT JOIN {task_tags_table_name} tt ON t.id = tt.task_id
    LEFT JOIN {tags_table_name} tg ON tt.tag_id = tg.id
    LEFT JOIN {organizations_table_name} o ON t.org_id = o.id"""

    query_params = ()
    if org_id is not None:
        query += " WHERE t.org_id = ?"
        query_params += (org_id,)
        query += f"""
        GROUP BY t.id
        ORDER BY t.timestamp ASC
        """
    elif course_id is not None:
        query += f""" 
        INNER JOIN {course_tasks_table_name} ct ON t.id = ct.task_id
        WHERE ct.course_id = ?
        GROUP BY t.id
        ORDER BY ct.ordering ASC
        """
        query_params += (course_id,)

    cursor.execute(
        query,
        query_params,
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
        tasks_dicts.append(convert_task_db_to_dict(row, tests))

    conn.close()

    return tasks_dicts


def get_all_verified_tasks_for_course(course_id: int, milestone_id: int = None):
    tasks = get_all_tasks_for_org_or_course(course_id=course_id)
    verified_tasks = [task for task in tasks if task["verified"]]

    if milestone_id:
        return [task for task in verified_tasks if task["milestone_id"] == milestone_id]

    return verified_tasks


def get_task_by_id(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
    SELECT t.id, t.name, t.description, t.answer, 
        GROUP_CONCAT(tg.name) as tags,
        t.type, t.coding_language, t.generation_model, t.verified, t.timestamp, m.id as milestone_id, COALESCE(m.name, '{uncategorized_milestone_name}') as milestone_name, t.org_id, o.name as org_name, t.response_type
    FROM {tasks_table_name} t
    LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
    LEFT JOIN {task_tags_table_name} tt ON t.id = tt.task_id 
    LEFT JOIN {tags_table_name} tg ON tt.tag_id = tg.id
    LEFT JOIN {organizations_table_name} o ON t.org_id = o.id
    WHERE t.id = ?
    GROUP BY t.id
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

    return convert_task_db_to_dict(task, tests)


def get_scoring_criteria_for_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT category, description, min_score, max_score FROM {task_scoring_criteria_table_name} WHERE task_id = ?",
        (task_id,),
    )

    rows = cursor.fetchall()

    return [
        {
            "category": row[0],
            "description": row[1],
            "range": [row[2], row[3]],
        }
        for row in rows
    ]


def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
        DELETE FROM {tests_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

        cursor.execute(
            f"""
        DELETE FROM {course_tasks_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

        cursor.execute(
            f"""
        DELETE FROM {task_tags_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

        cursor.execute(
            f"""
        DELETE FROM {chat_history_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

        cursor.execute(
            f"""
        DELETE FROM {task_scoring_criteria_table_name} WHERE task_id = ?
        """,
            (task_id,),
        )

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

    task_ids_as_str = serialise_list_to_str(map(str, task_ids))

    try:
        cursor.execute(
            f"""
        DELETE FROM {tests_table_name} WHERE task_id IN ({task_ids_as_str})
        """
        )

        cursor.execute(
            f"""
        DELETE FROM {course_tasks_table_name} WHERE task_id IN ({task_ids_as_str})
        """
        )

        cursor.execute(
            f"""
        DELETE FROM {task_tags_table_name} WHERE task_id IN ({task_ids_as_str})
        """
        )

        cursor.execute(
            f"""
        DELETE FROM {chat_history_table_name} WHERE task_id IN ({task_ids_as_str})
        """
        )

        cursor.execute(
            f"""
        DELETE FROM {task_scoring_criteria_table_name} WHERE task_id IN ({task_ids_as_str})
        """
        )

        cursor.execute(
            f"""
        DELETE FROM {tasks_table_name} WHERE id IN ({task_ids_as_str})
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
    user_id: int,
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
    SELECT message.id, message.timestamp, user.id AS user_id, user.email AS user_email, message.task_id, task.name AS task_name, message.role, message.content, message.is_solved, message.response_type
    FROM {chat_history_table_name} message
    INNER JOIN {tasks_table_name} task ON message.task_id = task.id
    INNER JOIN {users_table_name} user ON message.user_id = user.id
    ORDER BY message.timestamp ASC
    """
    )

    chat_history = cursor.fetchall()

    conn.close()

    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "user_id": row[2],
            "user_email": row[3],
            "task_id": row[4],
            "task_name": row[5],
            "role": row[6],
            "content": row[7],
            "is_solved": bool(row[8]),
            "response_type": row[9],
        }
        for row in chat_history
    ]


def get_task_chat_history_for_user(task_id: int, user_id: int):
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
    user_id: int,
    cohort_id: int,
    view_type: LeaderboardViewType = LeaderboardViewType.ALL_TIME,
):
    conn = get_db_connection()
    cursor = conn.cursor()

    if view_type == LeaderboardViewType.ALL_TIME:
        cursor.execute(
            f"""
        SELECT DISTINCT ch.task_id 
        FROM {chat_history_table_name} ch
        JOIN {tasks_table_name} t ON t.id = ch.task_id
        JOIN {course_tasks_table_name} ct ON t.id = ct.task_id
        JOIN {course_cohorts_table_name} cc ON ct.course_id = cc.course_id
        WHERE ch.user_id = ? AND ch.is_solved = 1 AND cc.cohort_id = ?
        """,
            (user_id, cohort_id),
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
            SELECT ch.task_id, MIN(datetime(ch.timestamp, '+5 hours', '+30 minutes')) as first_solved_time
            FROM {chat_history_table_name} ch
            JOIN {tasks_table_name} t ON t.id = ch.task_id
            JOIN {course_tasks_table_name} ct ON t.id = ct.task_id
            JOIN {course_cohorts_table_name} cc ON ct.course_id = cc.course_id
            WHERE ch.user_id = ? AND ch.is_solved = 1 AND cc.cohort_id = ?
            GROUP BY ch.task_id
        )
        SELECT DISTINCT task_id 
        FROM FirstSolved
        WHERE first_solved_time >= ?
        """,
            (user_id, cohort_id, start_date),
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


def delete_user_chat_history_for_task(task_id: int, user_id: int):
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


def get_user_activity_last_n_days(user_id: int, n: int, cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the user's interactions for the last n days, ordered by date
    cursor.execute(
        f"""
    SELECT DATE(datetime(timestamp, '+5 hours', '+30 minutes')), COUNT(*)
    FROM {chat_history_table_name}
    WHERE user_id = ? AND DATE(datetime(timestamp, '+5 hours', '+30 minutes')) >= DATE(datetime('now', '+5 hours', '+30 minutes'), '-{n} days') AND task_id IN (SELECT task_id FROM {course_tasks_table_name} WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?))
    GROUP BY DATE(timestamp)
    ORDER BY DATE(timestamp)
    """,
        (user_id, cohort_id),
    )

    activity_per_day = cursor.fetchall()
    conn.close()

    active_days = []

    for date, count in activity_per_day:
        if count > 0:
            active_days.append(datetime.strptime(date, "%Y-%m-%d"))

    return active_days


def get_user_streak(user_id: int, cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the user's interactions, ordered by timestamp
    cursor.execute(
        f"""
    SELECT MAX(datetime(timestamp, '+5 hours', '+30 minutes')) as timestamp
    FROM {chat_history_table_name}
    WHERE user_id = ? AND task_id IN (SELECT task_id FROM {course_tasks_table_name} WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?))
    GROUP BY DATE(datetime(timestamp, '+5 hours', '+30 minutes'))
    ORDER BY timestamp DESC
    """,
        (user_id, cohort_id),
    )

    user_usage_dates = cursor.fetchall()
    conn.close()

    return get_user_streak_from_usage_dates(
        [date_str for date_str, in user_usage_dates]
    )


def get_streaks(
    view: LeaderboardViewType = LeaderboardViewType.ALL_TIME, cohort_id: int = None
):
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
    SELECT 
        u.id,
        u.email,
        u.first_name,
        u.middle_name,
        u.last_name,
        GROUP_CONCAT(t.timestamp) as timestamps
    FROM (
        SELECT user_id, MAX(datetime(timestamp, '+5 hours', '+30 minutes')) as timestamp
        FROM {chat_history_table_name}
        WHERE 1=1 {date_filter} AND task_id IN (SELECT task_id FROM {course_tasks_table_name} WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?))
        GROUP BY user_id, DATE(datetime(timestamp, '+5 hours', '+30 minutes'))
        ORDER BY user_id, timestamp DESC
    ) t
    JOIN users u ON u.id = t.user_id
    GROUP BY u.email, u.first_name, u.middle_name, u.last_name
    """,
        (cohort_id,),
    )

    usage_per_user = cursor.fetchall()
    conn.close()

    streaks = []

    for (
        user_id,
        user_email,
        user_first_name,
        user_middle_name,
        user_last_name,
        user_usage_dates_str,
    ) in usage_per_user:
        user_usage_dates = user_usage_dates_str.split(",")
        streaks.append(
            {
                "user": {
                    "id": user_id,
                    "email": user_email,
                    "first_name": user_first_name,
                    "middle_name": user_middle_name,
                    "last_name": user_last_name,
                },
                "count": len(get_user_streak_from_usage_dates(user_usage_dates)),
            }
        )

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


def delete_cohort(cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"DELETE FROM {user_groups_table_name} WHERE group_id IN (SELECT id FROM {groups_table_name} WHERE cohort_id = ?)",
        (cohort_id,),
    )
    cursor.execute(f"DELETE FROM {groups_table_name} WHERE cohort_id = ?", (cohort_id,))
    cursor.execute(
        f"DELETE FROM {user_cohorts_table_name} WHERE cohort_id = ?", (cohort_id,)
    )
    cursor.execute(f"DELETE FROM {cohorts_table_name} WHERE id = ?", (cohort_id,))
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


def create_cohort(name: str, org_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            INSERT INTO {cohorts_table_name} (name, org_id)
            VALUES (?, ?)
            """,
            (name, org_id),
        )
        cohort_id = cursor.lastrowid
        conn.commit()

        return cohort_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def add_members_to_cohort(cohort_id: int, emails: List[str], roles: List[str]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        users_to_add = []
        for email in emails:
            # Get or create user
            user = insert_or_return_user(email, conn, cursor)
            users_to_add.append(user["id"])

        # Add users to cohort
        cursor.executemany(
            f"""
            INSERT INTO {user_cohorts_table_name} (user_id, cohort_id, role)
            VALUES (?, ?, ?)
            """,
            [(user_id, cohort_id, role) for user_id, role in zip(users_to_add, roles)],
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_cohort_group_name(group_id: int, new_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"UPDATE {groups_table_name} SET name = ? WHERE id = ?",
            (new_name, group_id),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def add_members_to_cohort_group(
    group_id: int, member_ids: List[int], conn=None, cursor=None
):
    is_master_connection = False
    if conn is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_master_connection = True

    try:
        cursor.executemany(
            f"INSERT INTO {user_groups_table_name} (user_id, group_id) VALUES (?, ?)",
            [(member_id, group_id) for member_id in member_ids],
        )
        if is_master_connection:
            conn.commit()
    except Exception as e:
        if is_master_connection:
            conn.rollback()
        raise e
    finally:
        if is_master_connection:
            conn.close()


def remove_members_from_cohort_group(group_id: int, member_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"DELETE FROM {user_groups_table_name} WHERE group_id = ? AND user_id IN ({','.join(['?' for _ in member_ids])})",
            (group_id, *member_ids),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_cohort_group(name: str, cohort_id: int, member_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create the group
        cursor.execute(
            f"""
            INSERT INTO {groups_table_name} (name, cohort_id)
            VALUES (?, ?)
            """,
            (name, cohort_id),
        )
        group_id = cursor.lastrowid

        add_members_to_cohort_group(group_id, member_ids, conn, cursor)

        conn.commit()
        return group_id

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def delete_cohort_group_from_db(group_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"DELETE FROM {user_groups_table_name} WHERE group_id = ?", (group_id,)
        )
        cursor.execute(f"DELETE FROM {groups_table_name} WHERE id = ?", (group_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def remove_members_from_cohort(cohort_id: int, member_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Remove users from cohort groups
        cursor.execute(
            f"""
            DELETE FROM {user_groups_table_name} 
            WHERE user_id IN ({','.join(['?' for _ in member_ids])})
            AND group_id IN (
                SELECT id FROM {groups_table_name} 
                WHERE cohort_id = ?
            )
            """,
            (*member_ids, cohort_id),
        )
        # Remove users from cohort
        cursor.execute(
            f"""
            DELETE FROM {user_cohorts_table_name}
            WHERE user_id IN ({','.join(['?' for _ in member_ids])})
            AND cohort_id = ?
            """,
            (*member_ids, cohort_id),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_cohorts_for_org(org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT c.id, c.name
            FROM {cohorts_table_name} c
            WHERE c.org_id = ?
            ORDER BY c.id DESC
            """,
            (org_id,),
        )

        cohorts = cursor.fetchall()

        return [{"id": row[0], "name": row[1]} for row in cohorts]
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

        cursor.execute(
            f"""
            SELECT 
                g.id,
                g.name,
                GROUP_CONCAT(COALESCE(u.id, '')) as user_ids,
                GROUP_CONCAT(COALESCE(u.email, '')) as user_emails,
                GROUP_CONCAT(COALESCE(uc.role, '')) as user_roles
            FROM {groups_table_name} g
            LEFT JOIN {user_groups_table_name} ug ON g.id = ug.group_id 
            LEFT JOIN {users_table_name} u ON ug.user_id = u.id
            LEFT JOIN {user_cohorts_table_name} uc ON uc.user_id = u.id AND uc.cohort_id = g.cohort_id
            WHERE g.cohort_id = ?
            GROUP BY g.id, g.name
            ORDER BY g.id
            """,
            (cohort_id,),
        )
        groups = cursor.fetchall()

        # Get all users and their roles in the cohort
        cursor.execute(
            f"""
            SELECT DISTINCT u.id, u.email, uc.role
            FROM {users_table_name} u
            JOIN {user_cohorts_table_name} uc ON u.id = uc.user_id 
            WHERE uc.cohort_id = ?
            ORDER BY uc.role
            """,
            (cohort_id,),
        )

        members = cursor.fetchall()

        cohort_data = {
            "id": cohort[0],
            "name": cohort[1],
            "members": [
                {"id": member[0], "email": member[1], "role": member[2]}
                for member in members
            ],
            "groups": [
                {
                    "id": group[0],
                    "name": group[1],
                    "members": [
                        {"id": int(user_id), "email": user_email, "role": user_role}
                        for user_id, user_email, user_role in zip(
                            group[2].split(","),
                            group[3].split(","),
                            group[4].split(","),
                        )
                        if user_id != ""
                    ],
                }
                for group in groups
            ],
        }

        return cohort_data
    except Exception as e:
        print(f"Error fetching cohort details: {e}")
        traceback.print_exc()
        return None
    finally:
        conn.close()


def delete_user_from_cohort(user_id: int, cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"DELETE FROM {user_groups_table_name} WHERE user_id = ? AND group_id IN (SELECT id FROM {groups_table_name} WHERE cohort_id = ?)",
        (user_id, cohort_id),
    )
    cursor.execute(
        f"DELETE FROM {user_cohorts_table_name} WHERE user_id = ? AND cohort_id = ?",
        (user_id, cohort_id),
    )

    conn.commit()
    conn.close()


def format_user_cohort_group(group: Tuple):
    learners = []
    for id, email in zip(group[2].split(","), group[3].split(",")):
        learners.append({"id": int(id), "email": email})

    return {
        "id": group[0],
        "name": group[1],
        "learners": learners,
    }


def get_user_cohort_groups(user_id: int, cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        WITH mentor_groups AS (
            SELECT g.id as group_id, g.name as group_name, g.cohort_id as cohort_id
            FROM {user_groups_table_name} ug
            JOIN {groups_table_name} g ON ug.group_id = g.id
            JOIN {user_cohorts_table_name} uc ON uc.user_id = ug.user_id AND uc.cohort_id = g.cohort_id
            WHERE ug.user_id = ? AND uc.role = '{group_role_mentor}' AND g.cohort_id = ?
        ),
        learners AS (
            SELECT mg.group_id, mg.group_name, GROUP_CONCAT(u.email) as learner_emails, GROUP_CONCAT(u.id) as learner_ids
            FROM mentor_groups mg
            JOIN {user_groups_table_name} ug ON ug.group_id = mg.group_id 
            JOIN {users_table_name} u ON u.id = ug.user_id
            JOIN {user_cohorts_table_name} uc ON uc.user_id = ug.user_id AND uc.cohort_id = mg.cohort_id
            WHERE uc.role = '{group_role_learner}'
            GROUP BY mg.group_id, mg.group_name
        )
        SELECT group_id, group_name, learner_ids, learner_emails
        FROM learners
        """,
        (user_id, cohort_id),
    )
    groups = cursor.fetchall()

    return [format_user_cohort_group(group) for group in groups]


def convert_milestone_db_to_dict(milestone: Tuple) -> Dict:
    return {"id": milestone[0], "name": milestone[1], "color": milestone[2]}


def get_all_milestones():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {milestones_table_name}")
    milestones = cursor.fetchall()

    conn.close()

    return [convert_milestone_db_to_dict(milestone) for milestone in milestones]


def get_all_milestones_for_org(org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {milestones_table_name} WHERE org_id = ?", (org_id,))
    milestones = cursor.fetchall()

    conn.close()

    return [convert_milestone_db_to_dict(milestone) for milestone in milestones]


def insert_milestone(name: str, color: str, org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {milestones_table_name} (name, color, org_id) VALUES (?, ?, ?)",
        (name, color, org_id),
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


def get_all_milestone_progress(user_id: int, course_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    base_query = f"""
    SELECT 
        m.id AS milestone_id,
        m.name AS milestone_name,
        m.color AS milestone_color,
        COUNT(DISTINCT t.id) AS total_tasks,
        SUM(DISTINCT CASE WHEN task_solved.is_solved = 1 THEN 1 ELSE 0 END) AS completed_tasks,
        COUNT(DISTINCT t.id) - SUM(DISTINCT CASE WHEN task_solved.is_solved = 1 THEN 1 ELSE 0 END) AS incomplete_tasks
    FROM 
        {milestones_table_name} m
    LEFT JOIN 
        {tasks_table_name} t ON m.id = t.milestone_id
    LEFT JOIN
        {course_tasks_table_name} ct ON t.id = ct.task_id
    LEFT JOIN {course_cohorts_table_name} cc ON ct.course_id = cc.course_id
    LEFT JOIN (
        SELECT 
            task_id, 
            user_id, 
            MAX(CASE WHEN is_solved = 1 THEN 1 ELSE 0 END) AS is_solved
        FROM 
            {chat_history_table_name}
        WHERE 
            user_id = ? AND task_id IN (
                SELECT task_id FROM {course_tasks_table_name} WHERE course_id = ?
            )
        GROUP BY 
            task_id, user_id
    ) task_solved ON t.id = task_solved.task_id
    WHERE 
        t.verified = 1 AND ct.course_id = ?
    GROUP BY 
        m.id, m.name, m.color
    HAVING 
        COUNT(DISTINCT t.id) > 0
    ORDER BY 
        ct.ordering
    """

    params = [user_id, course_id, course_id]

    cursor.execute(base_query, tuple(params))
    results = cursor.fetchall()
    print(base_query)
    print(params)
    print(results)

    # Get tasks with null milestone_id
    null_milestone_query = f"""
    SELECT 
        NULL AS milestone_id,
        '{uncategorized_milestone_name}' AS milestone_name,
        '{uncategorized_milestone_color}' AS milestone_color,
        COUNT(DISTINCT t.id) AS total_tasks,
        SUM(DISTINCT CASE WHEN task_solved.is_solved = 1 THEN 1 ELSE 0 END) AS completed_tasks,
        COUNT(DISTINCT t.id) - SUM(DISTINCT CASE WHEN task_solved.is_solved = 1 THEN 1 ELSE 0 END) AS incomplete_tasks
    FROM 
        {tasks_table_name} t
    LEFT JOIN
        {course_tasks_table_name} ct ON t.id = ct.task_id
    LEFT JOIN {course_cohorts_table_name} cc ON ct.course_id = cc.course_id
    LEFT JOIN (
        SELECT 
            task_id,
            user_id,
            MAX(CASE WHEN is_solved = 1 THEN 1 ELSE 0 END) AS is_solved
        FROM 
            {chat_history_table_name}
        WHERE 
            user_id = ? AND task_id IN (
                SELECT task_id FROM {course_tasks_table_name} WHERE course_id = ?
            )
        GROUP BY 
            task_id, user_id
    ) task_solved ON t.id = task_solved.task_id
    WHERE 
        t.milestone_id IS NULL 
        AND t.verified = 1 
        AND ct.course_id = ?
    HAVING
        COUNT(DISTINCT t.id) > 0
    ORDER BY 
        ct.ordering
    """

    null_params = [user_id, course_id, course_id]

    cursor.execute(null_milestone_query, tuple(null_params))
    null_milestone_results = cursor.fetchall()

    results.extend(null_milestone_results)

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


def insert_or_return_user(email: str, conn=None, cursor=None):
    is_master_connection = False
    if conn is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_master_connection = True

    try:
        # if user exists, no need to do anything, just return the user
        cursor.execute(
            f"""SELECT * FROM {users_table_name} WHERE email = ?""",
            (email,),
        )

        user = cursor.fetchone()

        if user:
            return convert_user_db_to_dict(user)

        # create a new user
        color = generate_random_color()
        cursor.execute(
            f"""
            INSERT INTO {users_table_name} (email, default_dp_color)
            VALUES (?, ?)
        """,
            (email, color),
        )

        cursor.execute(
            f"""SELECT * FROM {users_table_name} WHERE email = ?""",
            (email,),
        )

        user = convert_user_db_to_dict(cursor.fetchone())

        # create a new organization for the user (Personal Workspace)
        create_organization_with_user(
            org_name="Personal Workspace",
            user_id=user["id"],
            conn=conn,
            cursor=cursor,
        )
        if is_master_connection:
            conn.commit()

        return user

    except Exception as e:
        if is_master_connection:
            conn.rollback()
        raise e
    finally:
        if is_master_connection:
            conn.close()


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


def get_user_cohorts(user_id: int) -> List[Dict]:
    """Get all cohorts (and the groups in each cohort) that the user is a part of along with their role in each group"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all cohorts and groups the user is a member of
    cursor.execute(
        f"""
        SELECT c.id, c.name, uc.role, o.id, o.name
        FROM {cohorts_table_name} c
        JOIN {user_cohorts_table_name} uc ON uc.cohort_id = c.id
        JOIN {organizations_table_name} o ON o.id = c.org_id
        WHERE uc.user_id = ?
    """,
        (user_id,),
    )

    results = cursor.fetchall()
    conn.close()

    # Convert results into nested dict structure
    return [
        {
            "id": cohort_id,
            "name": cohort_name,
            "org_id": org_id,
            "org_name": org_name,
            "role": role,
        }
        for cohort_id, cohort_name, role, org_id, org_name in results
    ]


def get_cohorts_for_org(org_id: int) -> List[Dict]:
    """Get all cohorts that belong to an organization"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all cohorts and groups the user is a member of
    cursor.execute(
        f"""
        SELECT c.id, c.name, o.id, o.name
        FROM {cohorts_table_name} c
        JOIN {organizations_table_name} o ON o.id = c.org_id
        WHERE o.id = ?
    """,
        (org_id,),
    )

    results = cursor.fetchall()
    conn.close()

    # Convert results into nested dict structure
    return [
        {"id": cohort_id, "name": cohort_name, "org_id": org_id, "org_name": org_name}
        for cohort_id, cohort_name, org_id, org_name in results
    ]


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


def add_cv_review_usage(user_id: int, role: str, ai_review: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {cv_review_usage_table_name} (user_id, role, ai_review) VALUES (?, ?, ?)",
        (user_id, role, ai_review),
    )
    conn.commit()
    conn.close()


def transform_cv_review_usage_to_dict(cv_review_usage: Tuple):
    return {
        "id": cv_review_usage[0],
        "user_id": cv_review_usage[1],
        "user_email": cv_review_usage[2],
        "role": cv_review_usage[3],
        "ai_review": cv_review_usage[4],
        "created_at": convert_utc_to_ist(
            datetime.fromisoformat(cv_review_usage[5])
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
        SELECT cv.id, cv.user_id, u.email, cv.role, cv.ai_review , cv.created_at
        FROM {cv_review_usage_table_name} cv
        JOIN users u ON cv.user_id = u.id
    """
    )
    all_cv_review_usage = cursor.fetchall()

    return [
        transform_cv_review_usage_to_dict(cv_review_usage)
        for cv_review_usage in all_cv_review_usage
    ]


def drop_organizations_table():
    drop_user_organizations_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {organizations_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {organizations_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def drop_user_organizations_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {user_organizations_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {user_organizations_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_organization(name: str, color: str = None, conn=None, cursor=None):
    slug = slugify(name) + "-" + str(uuid.uuid4())
    default_logo_color = color or generate_random_color()

    is_master_connection = False
    if conn is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_master_connection = True

    try:
        cursor.execute(
            f"""INSERT INTO {organizations_table_name} 
                (slug, name, default_logo_color)
                VALUES (?, ?, ?)""",
            (slug, name, default_logo_color),
        )
        if is_master_connection:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        if is_master_connection:
            conn.close()


def create_organization_with_user(
    org_name: str, user_id: int, color: str = None, conn=None, cursor=None
):
    org_id = create_organization(org_name, color, conn, cursor)
    add_user_to_org_by_user_id(user_id, org_id, "owner", conn, cursor)
    return org_id


def convert_org_db_to_dict(org: Tuple):
    return {
        "id": org[0],
        "slug": org[1],
        "name": org[2],
        "logo_color": org[3],
    }


def get_org_by_id(org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {organizations_table_name} WHERE id = ?", (org_id,))
    org_details = cursor.fetchone()

    return convert_org_db_to_dict(org_details)


def add_user_to_org_by_user_id(
    user_id: int,
    org_id: int,
    role: Literal["owner", "admin"],
    conn=None,
    cursor=None,
):
    is_master_connection = False
    if conn is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        is_master_connection = True

    try:
        cursor.execute(
            f"""INSERT INTO {user_organizations_table_name}
                (user_id, org_id, role)
                VALUES (?, ?, ?)""",
            (user_id, org_id, role),
        )
        if is_master_connection:
            conn.commit()

        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        if is_master_connection:
            conn.close()


def add_user_to_org_by_email(
    email: str,
    org_id: int,
    role: Literal["owner", "admin"],
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user = insert_or_return_user(email, conn, cursor)

        cursor.execute(
            f"""INSERT INTO {user_organizations_table_name}
                (user_id, org_id, role)
                VALUES (?, ?, ?)""",
            (user["id"], org_id, role),
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def convert_user_organization_db_to_dict(user_organization: Tuple):
    return {
        "id": user_organization[0],
        "user_id": user_organization[1],
        "org_id": user_organization[2],
        "role": user_organization[3],
    }


def get_user_organizations(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""SELECT uo.org_id, o.name, uo.role
        FROM {user_organizations_table_name} uo
        JOIN organizations o ON uo.org_id = o.id 
        WHERE uo.user_id = ? ORDER BY uo.id DESC""",
        (user_id,),
    )
    user_organizations = cursor.fetchall()

    return [
        {
            "id": user_organization[0],
            "name": user_organization[1],
            "role": user_organization[2],
        }
        for user_organization in user_organizations
    ]


def get_org_users(org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""SELECT uo.user_id, u.email, uo.role 
        FROM {user_organizations_table_name} uo
        JOIN users u ON uo.user_id = u.id 
        WHERE uo.org_id = ?""",
        (org_id,),
    )
    org_users = cursor.fetchall()

    return [
        {
            "id": org_user[0],
            "email": org_user[1],
            "role": org_user[2],
        }
        for org_user in org_users
    ]


def get_all_user_organizations():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {user_organizations_table_name}")
    user_organizations = cursor.fetchall()

    return [
        convert_user_organization_db_to_dict(user_organization)
        for user_organization in user_organizations
    ]


def drop_task_tags_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {task_tags_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {task_tags_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def drop_tags_table():
    drop_task_tags_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"DELETE FROM {tags_table_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {tags_table_name}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_tag(tag_name: str, org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {tags_table_name} (name, org_id) VALUES (?, ?)",
        (tag_name, org_id),
    )
    conn.commit()
    conn.close()


def create_bulk_tags(tag_names: List[str], org_id: int) -> bool:
    if not tag_names:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get existing tags
    cursor.execute(f"SELECT name FROM {tags_table_name} WHERE org_id = ?", (org_id,))
    existing_tags = {row[0] for row in cursor.fetchall()}

    # Filter out tags that already exist
    new_tags = [tag for tag in tag_names if tag not in existing_tags]

    has_new_tags = len(new_tags) > 0

    # Insert new tags
    if new_tags:
        cursor.executemany(
            f"INSERT INTO {tags_table_name} (name, org_id) VALUES (?, ?)",
            [(tag, org_id) for tag in new_tags],
        )

    conn.commit()
    conn.close()

    return has_new_tags


def convert_tag_db_to_dict(tag: Tuple) -> Dict:
    return {
        "id": tag[0],
        "name": tag[1],
        "created_at": convert_utc_to_ist(datetime.fromisoformat(tag[2])).isoformat(),
    }


def get_all_tags() -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {tags_table_name}")
    tags = cursor.fetchall()
    conn.close()

    return [convert_tag_db_to_dict(tag) for tag in tags]


def get_all_tags_for_org(org_id: int) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {tags_table_name} WHERE org_id = ?", (org_id,))
    tags = cursor.fetchall()
    conn.close()

    return [convert_tag_db_to_dict(tag) for tag in tags]


def delete_tag(tag_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {tags_table_name} WHERE id = ?", (tag_id,))
    conn.commit()
    conn.close()


def transfer_badge_to_user(prev_user_id: int, new_user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {badges_table_name} SET user_id = ? WHERE user_id = ?",
        (new_user_id, prev_user_id),
    )
    conn.commit()
    conn.close()


def transfer_chat_history_to_user(prev_user_id: int, new_user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {chat_history_table_name} SET user_id = ? WHERE user_id = ?",
        (new_user_id, prev_user_id),
    )
    conn.commit()
    conn.close()


def drop_user_cohorts_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"DROP TABLE IF EXISTS {user_cohorts_table_name}")
    conn.commit()
    conn.close()


def get_courses_for_tasks(task_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT ct.task_id, c.id, c.name FROM {course_tasks_table_name} ct JOIN {courses_table_name} c ON ct.course_id = c.id WHERE ct.task_id IN ({', '.join(map(str, task_ids))})"
    )
    results = cursor.fetchall()

    task_courses = [
        {
            "task_id": result[0],
            "course": {"id": result[1], "name": result[2]},
        }
        for result in results
    ]

    task_id_to_courses = defaultdict(list)

    for task_course in task_courses:
        task_id_to_courses[task_course["task_id"]].append(task_course["course"])

    return task_id_to_courses


def add_tasks_to_courses(course_tasks_to_add: List[Tuple[int, int]]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Group tasks by course_id
        course_to_tasks = defaultdict(list)
        for task_id, course_id in course_tasks_to_add:
            course_to_tasks[course_id].append(task_id)

        # For each course, get max ordering and insert tasks with incremented order
        for course_id, task_ids in course_to_tasks.items():
            cursor.execute(
                f"SELECT COALESCE(MAX(ordering), -1) FROM {course_tasks_table_name} WHERE course_id = ?",
                (course_id,),
            )
            max_ordering = cursor.fetchone()[0]

            # Insert tasks with incremented ordering
            values_to_insert = []
            for i, task_id in enumerate(task_ids, start=1):
                values_to_insert.append((task_id, course_id, max_ordering + i))

            cursor.executemany(
                f"INSERT OR IGNORE INTO {course_tasks_table_name} (task_id, course_id, ordering) VALUES (?, ?, ?)",
                values_to_insert,
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def remove_tasks_from_courses(course_tasks_to_remove: List[Tuple[int, int]]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.executemany(
            f"DELETE FROM {course_tasks_table_name} WHERE task_id = ? AND course_id = ?",
            course_tasks_to_remove,
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_task_orders(task_orders: List[Tuple[int, int]]):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.executemany(
            f"UPDATE {course_tasks_table_name} SET ordering = ? WHERE id = ?",
            task_orders,
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def add_scoring_criteria_to_task(task_id: int, scoring_criteria: List[Dict]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executemany(
        f"""INSERT INTO {task_scoring_criteria_table_name} 
            (task_id, category, description, min_score, max_score) 
            VALUES (?, ?, ?, ?, ?)""",
        [
            (
                task_id,
                criterion["category"],
                criterion["description"],
                criterion["range"][0],
                criterion["range"][1],
            )
            for criterion in scoring_criteria
        ],
    )

    conn.commit()
    conn.close()


def add_scoring_criteria_to_tasks(task_ids: List[int], scoring_criteria: List[Dict]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executemany(
        f"""INSERT INTO {task_scoring_criteria_table_name} 
            (task_id, category, description, min_score, max_score) 
            VALUES (?, ?, ?, ?, ?)""",
        list(
            itertools.chain(
                *[
                    [
                        (
                            task_id,
                            criterion["category"],
                            criterion["description"],
                            criterion["range"][0],
                            criterion["range"][1],
                        )
                        for criterion in scoring_criteria
                    ]
                    for task_id in task_ids
                ]
            )
        ),
    )

    conn.commit()
    conn.close()


def create_course(name: str, org_id: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            INSERT INTO {courses_table_name} (name, org_id)
            VALUES (?, ?)
            """,
            (name, org_id),
        )
        cohort_id = cursor.lastrowid
        conn.commit()

        return cohort_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_course_name(course_id: int, name: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {courses_table_name} SET name = ? WHERE id = ?", (name, course_id)
    )

    conn.commit()
    conn.close()


def update_cohort_name(cohort_id: int, name: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"UPDATE {cohorts_table_name} SET name = ? WHERE id = ?", (name, cohort_id)
    )

    conn.commit()
    conn.close()


def convert_course_db_to_dict(course: Tuple) -> Dict:
    return {
        "id": course[0],
        "name": course[1],
    }


def get_all_courses_for_org(org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"SELECT id, name FROM {courses_table_name} WHERE org_id = ? ORDER BY id DESC",
            (org_id,),
        )

        courses = cursor.fetchall()

        return [convert_course_db_to_dict(course) for course in courses]
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return []
    finally:
        conn.close()


def delete_course(course_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"DELETE FROM {course_cohorts_table_name} WHERE course_id = ?", (course_id,)
    )

    cursor.execute(f"DELETE FROM {courses_table_name} WHERE id = ?", (course_id,))

    conn.commit()
    conn.close()


def delete_all_courses_for_org(org_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"DELETE FROM {course_cohorts_table_name} WHERE course_id IN (SELECT id FROM {courses_table_name} WHERE org_id = ?)",
        (org_id,),
    )

    cursor.execute(f"DELETE FROM {courses_table_name} WHERE org_id = ?", (org_id,))

    conn.commit()
    conn.close()


def add_course_to_cohorts(course_id: int, cohort_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executemany(
        f"INSERT INTO {course_cohorts_table_name} (course_id, cohort_id) VALUES (?, ?)",
        [(course_id, cohort_id) for cohort_id in cohort_ids],
    )

    conn.commit()
    conn.close()


def add_courses_to_cohort(cohort_id: int, course_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executemany(
        f"INSERT INTO {course_cohorts_table_name} (course_id, cohort_id) VALUES (?, ?)",
        [(course_id, cohort_id) for course_id in course_ids],
    )

    conn.commit()
    conn.close()


def remove_course_from_cohorts(course_id: int, cohort_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executemany(
        f"DELETE FROM {course_cohorts_table_name} WHERE course_id = ? AND cohort_id = ?",
        [(course_id, cohort_id) for cohort_id in cohort_ids],
    )

    conn.commit()
    conn.close()


def remove_courses_from_cohort(cohort_id: int, course_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executemany(
        f"DELETE FROM {course_cohorts_table_name} WHERE cohort_id = ? AND course_id = ?",
        [(cohort_id, course_id) for course_id in course_ids],
    )

    conn.commit()
    conn.close()


@st.cache_data
def get_courses_for_cohort(cohort_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT c.id, c.name 
        FROM {courses_table_name} c
        JOIN {course_cohorts_table_name} cc ON c.id = cc.course_id
        WHERE cc.cohort_id = ?
        """,
        (cohort_id,),
    )

    courses = cursor.fetchall()
    return [{"id": course[0], "name": course[1]} for course in courses]


@st.cache_data
def get_cohorts_for_course(course_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT ch.id, ch.name 
        FROM {cohorts_table_name} ch
        JOIN {course_cohorts_table_name} cc ON ch.id = cc.cohort_id
        WHERE cc.course_id = ?
        """,
        (course_id,),
    )

    cohorts = cursor.fetchall()
    return [{"id": cohort[0], "name": cohort[1]} for cohort in cohorts]


def drop_course_cohorts_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {course_cohorts_table_name}")
    cursor.execute(f"DROP TABLE IF EXISTS {course_cohorts_table_name}")

    conn.commit()
    conn.close()


def drop_courses_table():
    drop_course_cohorts_table()

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM {courses_table_name}")
    cursor.execute(f"DROP TABLE IF EXISTS {courses_table_name}")

    conn.commit()
    conn.close()


def get_tasks_for_course(course_id: int, milestone_id: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = f"""SELECT t.id, t.name, COALESCE(m.name, '{uncategorized_milestone_name}') as milestone_name, t.verified, t.type, t.response_type, t.coding_language, ct.ordering, ct.id as course_task_id
        FROM {course_tasks_table_name} ct 
        JOIN {tasks_table_name} t ON ct.task_id = t.id 
        LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
        WHERE ct.course_id = ?"""

    params = [course_id]

    if milestone_id is not None:
        query += " AND t.milestone_id = ?"
        params.append(milestone_id)

    query += " ORDER BY ct.ordering"

    cursor.execute(query, tuple(params))

    tasks = cursor.fetchall()
    return [
        {
            "id": task[0],
            "name": task[1],
            "milestone": task[2],
            "verified": task[3],
            "type": task[4],
            "response_type": task[5],
            "coding_language": deserialise_list_from_str(task[6]),
            "ordering": task[7],
            "course_task_id": task[8],
        }
        for task in tasks
    ]
