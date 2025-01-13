import os
from os.path import exists
import json
from collections import defaultdict
import streamlit as st
import traceback
import itertools
import sqlite3
from contextlib import contextmanager
import uuid
import queue
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
from lib.utils.encryption import encrypt_openai_api_key
from lib.url import slugify
from lib.utils.db import (
    execute_db_operation,
    get_new_db_connection,
    check_table_exists,
    get_shared_db_connection,
    serialise_list_to_str,
    deserialise_list_from_str,
    execute_multiple_db_operations,
    execute_many_db_operation,
)


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
                openai_api_key TEXT,
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
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id),
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
                cohort_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id),
                FOREIGN KEY (cohort_id) REFERENCES {cohorts_table_name}(id)
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
                FOREIGN KEY (group_id) REFERENCES {groups_table_name}(id),
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
                color TEXT,
                FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
            )"""
    )


def create_tag_tables(cursor):
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS {tags_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
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
                FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id),
                FOREIGN KEY (tag_id) REFERENCES {tags_table_name}(id)
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
                    input_type TEXT,
                    coding_language TEXT,
                    generation_model TEXT,
                    verified BOOLEAN NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    milestone_id INTEGER,
                    org_id INTEGER NOT NULL,
                    response_type TEXT,
                    context TEXT,
                    deleted_at DATETIME,
                    type TEXT,
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
                    content TEXT,
                    is_solved BOOLEAN NOT NULL DEFAULT 0,
                    response_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id),
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
                FOREIGN KEY (user_id) REFERENCES {users_table_name}(id)
            )
            """
    )


def init_db():
    # Ensure the database folder exists
    db_folder = os.path.dirname(sqlite_db_path)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    with get_shared_db_connection() as conn:
        cursor = conn.cursor()

        if exists(sqlite_db_path):
            if not check_table_exists(organizations_table_name, cursor):
                create_organizations_table(cursor)

            if not check_table_exists(users_table_name, cursor):
                create_users_table(cursor)

            if not check_table_exists(user_organizations_table_name, cursor):
                create_user_organizations_table(cursor)

            if not check_table_exists(cohorts_table_name, cursor):
                create_cohort_tables(cursor)

            if not check_table_exists(courses_table_name, cursor):
                create_courses_table(cursor)

            if not check_table_exists(course_cohorts_table_name, cursor):
                create_course_cohorts_table(cursor)

            if not check_table_exists(milestones_table_name, cursor):
                create_milestones_table(cursor)

            if not check_table_exists(tags_table_name, cursor):
                create_tag_tables(cursor)

            if not check_table_exists(badges_table_name, cursor):
                create_badges_table(cursor)

            if not check_table_exists(tasks_table_name, cursor):
                create_tasks_table(cursor)

            if not check_table_exists(task_scoring_criteria_table_name, cursor):
                create_task_scoring_criteria_table(cursor)

            if not check_table_exists(tests_table_name, cursor):
                create_tests_table(cursor)

            if not check_table_exists(chat_history_table_name, cursor):
                create_chat_history_table(cursor)

            if not check_table_exists(course_tasks_table_name, cursor):
                create_course_tasks_table(cursor)

            if not check_table_exists(cv_review_usage_table_name, cursor):
                create_cv_review_usage_table(cursor)

            conn.commit()
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

            conn.commit()

        except Exception as exception:
            # delete db
            conn.rollback()
            os.remove(sqlite_db_path)
            raise exception


def add_tags_to_task(task_id: int, tag_ids_to_add: List):
    if not tag_ids_to_add:
        return

    execute_many_db_operation(
        f"INSERT INTO {task_tags_table_name} (task_id, tag_id) VALUES (?, ?)",
        [(task_id, tag_id) for tag_id in tag_ids_to_add],
    )


def remove_tags_from_task(task_id: int, tag_ids_to_remove: List):
    if not tag_ids_to_remove:
        return

    execute_db_operation(
        f"DELETE FROM {task_tags_table_name} WHERE task_id = ? AND tag_id IN ({','.join(map(str, tag_ids_to_remove))})",
        (task_id,),
    )


def store_task(
    name: str,
    description: str,
    answer: str,
    tags: List[Dict],
    input_type: str,
    response_type: str,
    coding_languages: List[str],
    generation_model: str,
    verified: bool,
    tests: List[dict],
    milestone_id: int,
    org_id: int,
    context: str,
    task_type: str,
):
    coding_language_str = serialise_list_to_str(coding_languages)

    # Insert main task
    insert_task_query = f"""
    INSERT INTO {tasks_table_name} 
    (name, description, answer, input_type, coding_language, generation_model, verified, milestone_id, org_id, response_type, context, type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    task_params = (
        name,
        description,
        answer,
        input_type,
        coding_language_str,
        generation_model,
        verified,
        milestone_id,
        org_id,
        response_type,
        context,
        task_type,
    )

    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Insert task and get its ID
            cursor.execute(insert_task_query, task_params)
            task_id = cursor.lastrowid

            # Insert tags
            tag_query = (
                f"INSERT INTO {task_tags_table_name} (task_id, tag_id) VALUES (?, ?)"
            )
            tag_params = [(task_id, tag["id"]) for tag in tags]
            cursor.executemany(
                tag_query,
                tag_params,
            )

            if tests:
                # Insert test cases
                test_query = f"INSERT INTO {tests_table_name} (task_id, input, output, description) VALUES (?, ?, ?, ?)"
                test_params = [
                    (
                        task_id,
                        json.dumps(test["input"]),
                        test["output"],
                        test.get("description", None),
                    )
                    for test in tests
                ]
                cursor.executemany(test_query, test_params)

            conn.commit()
            return task_id
        except Exception as e:
            conn.rollback()
            raise e


def update_task(
    task_id: int,
    name: str,
    description: str,
    answer: str,
    input_type: str,
    response_type: str,
    coding_languages: List[str],
    milestone_id: int,
    context: str,
):
    coding_language_str = serialise_list_to_str(coding_languages)

    execute_db_operation(
        f"""
    UPDATE {tasks_table_name}
    SET name = ?, description = ?, answer = ?, input_type = ?, coding_language = ?, response_type = ?, milestone_id = ?, context = ?
    WHERE id = ?
    """,
        (
            name,
            description,
            answer,
            input_type,
            coding_language_str,
            response_type,
            milestone_id,
            context,
            task_id,
        ),
    )


def update_column_for_task_ids(task_ids: List[int], column_name: Any, new_value: Any):
    if isinstance(new_value, list):
        new_value = ",".join(new_value)

    execute_db_operation(
        f"""
    UPDATE {tasks_table_name}
    SET {column_name} = ?
    WHERE id IN ({','.join(map(str, task_ids))})
    """,
        (new_value,),
    )


def return_test_rows_as_dict(test_rows: List[Tuple[str, str, str]]) -> List[Dict]:
    return [
        {"input": json.loads(row[0]), "output": row[1], "description": row[2]}
        for row in test_rows
    ]


def convert_task_db_to_dict(task, tests):
    tag_ids = list(map(int, deserialise_list_from_str(task[17])))
    tag_names = deserialise_list_from_str(task[4])

    tags = [{"id": tag_ids[i], "name": tag_names[i]} for i in range(len(tag_ids))]

    return {
        "id": task[0],
        "name": task[1],
        "description": task[2],
        "answer": task[3],
        "tags": tags,
        "input_type": task[5],
        "coding_language": deserialise_list_from_str(task[6]),
        "generation_model": task[7],
        "verified": bool(task[8]),
        "timestamp": task[9],
        "milestone_id": task[10],
        "milestone_name": task[11],
        "org_id": task[12],
        "org_name": task[13],
        "response_type": task[14],
        "context": task[15],
        "type": task[16],
        "tests": tests,
    }


def get_all_tasks_for_org_or_course(org_id: int = None, course_id: int = None):
    if org_id is None and course_id is None:
        raise ValueError("Either org_id or course_id must be provided")
    if org_id is not None and course_id is not None:
        raise ValueError("Only one of org_id or course_id can be provided")

    query = f"""
    SELECT t.id, t.name, t.description, t.answer,
        GROUP_CONCAT(tg.name) as tag_names,
        t.input_type, t.coding_language, t.generation_model, t.verified, t.timestamp, m.id as milestone_id, m.name as milestone_name, o.id, o.name as org_name,
        t.response_type, t.context, t.type, GROUP_CONCAT(tg.id) as tag_ids
    FROM {tasks_table_name} t
    LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
    LEFT JOIN {task_tags_table_name} tt ON t.id = tt.task_id
    LEFT JOIN {tags_table_name} tg ON tt.tag_id = tg.id
    LEFT JOIN {organizations_table_name} o ON t.org_id = o.id"""

    query_params = ()
    if org_id is not None:
        query += " WHERE t.org_id = ? AND t.deleted_at IS NULL"
        query_params += (org_id,)
        query += f"""
        GROUP BY t.id
        ORDER BY t.timestamp ASC
        """
    elif course_id is not None:
        query += f""" 
        INNER JOIN {course_tasks_table_name} ct ON t.id = ct.task_id
        WHERE ct.course_id = ? AND t.deleted_at IS NULL
        GROUP BY t.id
        ORDER BY ct.ordering ASC
        """
        query_params += (course_id,)

    tasks = execute_db_operation(query, query_params, fetch_all=True)

    tasks_dicts = []
    for row in tasks:
        task_id = row[0]

        # Fetch associated tests for each task
        tests = execute_db_operation(
            f"""
            SELECT input, output, description FROM {tests_table_name} WHERE task_id = ?
            """,
            (task_id,),
            fetch_all=True,
        )

        tests = return_test_rows_as_dict(tests)
        tasks_dicts.append(convert_task_db_to_dict(row, tests))

    return tasks_dicts


def get_all_verified_tasks_for_course(course_id: int, milestone_id: int = None):
    tasks = get_all_tasks_for_org_or_course(course_id=course_id)
    verified_tasks = [task for task in tasks if task["verified"]]

    if milestone_id:
        return [task for task in verified_tasks if task["milestone_id"] == milestone_id]

    return verified_tasks


def get_task_by_id(task_id: int):
    task = execute_db_operation(
        f"""
    SELECT t.id, t.name, t.description, t.answer, 
        GROUP_CONCAT(tg.name) as tag_names,
        t.input_type, t.coding_language, t.generation_model, t.verified, t.timestamp, m.id as milestone_id, COALESCE(m.name, '{uncategorized_milestone_name}') as milestone_name, t.org_id, o.name as org_name, t.response_type, t.context, t.type, GROUP_CONCAT(tg.id) as tag_ids
    FROM {tasks_table_name} t
    LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
    LEFT JOIN {task_tags_table_name} tt ON t.id = tt.task_id 
    LEFT JOIN {tags_table_name} tg ON tt.tag_id = tg.id
    LEFT JOIN {organizations_table_name} o ON t.org_id = o.id
    WHERE t.id = ? AND t.deleted_at IS NULL
    GROUP BY t.id
    """,
        (task_id,),
        fetch_one=True,
    )

    if not task:
        return None

    # Fetch associated tests
    tests = execute_db_operation(
        f"""
    SELECT input, output, description FROM {tests_table_name} WHERE task_id = ?
    """,
        (task_id,),
        fetch_all=True,
    )

    tests = return_test_rows_as_dict(tests)

    return convert_task_db_to_dict(task, tests)


def get_scoring_criteria_for_task(task_id: int):
    rows = execute_db_operation(
        f"SELECT id, category, description, min_score, max_score FROM {task_scoring_criteria_table_name} WHERE task_id = ?",
        (task_id,),
        fetch_all=True,
    )

    return [
        {
            "id": row[0],
            "category": row[1],
            "description": row[2],
            "range": [row[3], row[4]],
        }
        for row in rows
    ]


def get_scoring_criteria_for_tasks(task_ids: List[int]):
    rows = execute_db_operation(
        f"""
        SELECT id, category, description, min_score, max_score, task_id 
        FROM {task_scoring_criteria_table_name} 
        WHERE task_id IN ({','.join(map(str, task_ids))})
        """,
        fetch_all=True,
    )

    # Group scoring criteria by task_id
    criteria_by_task = {}
    for row in rows:
        task_id = row[5]

        if task_id not in criteria_by_task:
            criteria_by_task[task_id] = []

        criteria_by_task[task_id].append(
            {
                "id": row[0],
                "category": row[1],
                "description": row[2],
                "range": [row[3], row[4]],
            }
        )

    # Return criteria in same order as input task_ids
    return [criteria_by_task.get(task_id, []) for task_id in task_ids]


def delete_task(task_id: int):
    execute_db_operation(
        f"""
        UPDATE {tasks_table_name} SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL
        """,
        (datetime.now(), task_id),
    )


def delete_tasks(task_ids: List[int]):
    task_ids_as_str = serialise_list_to_str(map(str, task_ids))

    execute_db_operation(
        f"""
        UPDATE {tasks_table_name} SET deleted_at = ? WHERE id IN ({task_ids_as_str}) AND deleted_at IS NULL
        """,
        (datetime.now(),),
    )


def store_message(
    user_id: int,
    task_id: int,
    role: str,
    content: str,
    is_solved: bool = False,
    response_type: str = None,
):
    # Insert the new message
    new_id = execute_db_operation(
        f"""
    INSERT INTO {chat_history_table_name} (user_id, task_id, role, content, is_solved, response_type)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
        (user_id, task_id, role, content, is_solved, response_type),
        get_last_row_id=True,
    )

    # Fetch the newly inserted row
    new_row = execute_db_operation(
        f"""
    SELECT id, timestamp, user_id, task_id, role, content, is_solved, response_type
    FROM {chat_history_table_name}
    WHERE id = ?
    """,
        (new_id,),
        fetch_one=True,
    )

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


def get_all_chat_history(org_id: int):
    chat_history = execute_db_operation(
        f"""
        SELECT message.id, message.timestamp, user.id AS user_id, user.email AS user_email, message.task_id, task.name AS task_name, message.role, message.content, message.is_solved, message.response_type
        FROM {chat_history_table_name} message
        INNER JOIN {tasks_table_name} task ON message.task_id = task.id
        INNER JOIN {users_table_name} user ON message.user_id = user.id 
        WHERE task.deleted_at IS NULL AND task.org_id = ?
        ORDER BY message.timestamp ASC
        """,
        (org_id,),
        fetch_all=True,
    )

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
    chat_history = execute_db_operation(
        f"""
    SELECT id, timestamp, user_id, task_id, role, content, is_solved, response_type FROM {chat_history_table_name} WHERE task_id = ? AND user_id = ?
    """,
        (task_id, user_id),
        fetch_all=True,
    )

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
    if view_type == LeaderboardViewType.ALL_TIME:
        results = execute_db_operation(
            f"""
        SELECT DISTINCT ch.task_id 
        FROM {chat_history_table_name} ch
        JOIN {tasks_table_name} t ON t.id = ch.task_id
        JOIN {course_tasks_table_name} ct ON t.id = ct.task_id
        JOIN {course_cohorts_table_name} cc ON ct.course_id = cc.course_id
        WHERE ch.user_id = ? AND ch.is_solved = 1 AND cc.cohort_id = ? AND t.deleted_at IS NULL
        """,
            (user_id, cohort_id),
            fetch_all=True,
        )
    else:
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        if view_type == LeaderboardViewType.WEEKLY:
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MONTHLY
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        results = execute_db_operation(
            f"""
        WITH FirstSolved AS (
            SELECT ch.task_id, MIN(datetime(ch.timestamp, '+5 hours', '+30 minutes')) as first_solved_time
            FROM {chat_history_table_name} ch
            JOIN {tasks_table_name} t ON t.id = ch.task_id
            JOIN {course_tasks_table_name} ct ON t.id = ct.task_id
            JOIN {course_cohorts_table_name} cc ON ct.course_id = cc.course_id
            WHERE ch.user_id = ? AND ch.is_solved = 1 AND cc.cohort_id = ? AND t.deleted_at IS NULL
            GROUP BY ch.task_id
        )
        SELECT DISTINCT task_id 
        FROM FirstSolved
        WHERE first_solved_time >= ?
        """,
            (user_id, cohort_id, start_date),
            fetch_all=True,
        )

    return [task[0] for task in results]


def delete_message(message_id: int):
    execute_db_operation(
        f"DELETE FROM {chat_history_table_name} WHERE id = ?", (message_id,)
    )


def update_message_timestamp(message_id: int, new_timestamp: datetime):
    execute_db_operation(
        f"UPDATE {chat_history_table_name} SET timestamp = ? WHERE id = ?",
        (new_timestamp, message_id),
    )


def delete_user_chat_history_for_task(task_id: int, user_id: int):
    execute_db_operation(
        f"DELETE FROM {chat_history_table_name} WHERE task_id = ? AND user_id = ?",
        (task_id, user_id),
    )


def delete_all_chat_history():
    execute_db_operation(f"DELETE FROM {chat_history_table_name}")


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


def get_user_active_in_last_n_days(user_id: int, n: int, cohort_id: int):
    activity_per_day = execute_db_operation(
        f"""
    SELECT DATE(datetime(timestamp, '+5 hours', '+30 minutes')), COUNT(*)
    FROM {chat_history_table_name}
    WHERE user_id = ? AND DATE(datetime(timestamp, '+5 hours', '+30 minutes')) >= DATE(datetime('now', '+5 hours', '+30 minutes'), '-{n} days') AND task_id IN (SELECT task_id FROM {course_tasks_table_name} WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?))
    GROUP BY DATE(timestamp)
    ORDER BY DATE(timestamp)
    """,
        (user_id, cohort_id),
        fetch_all=True,
    )

    active_days = []

    for date, count in activity_per_day:
        if count > 0:
            active_days.append(datetime.strptime(date, "%Y-%m-%d"))

    return active_days


def get_user_activity_for_year(user_id: int, year: int):
    # Get all chat messages for the user in the given year, grouped by day
    activity_per_day = execute_db_operation(
        f"""
        SELECT 
            strftime('%j', datetime(timestamp, '+5 hours', '+30 minutes')) as day_of_year,
            COUNT(*) as message_count
        FROM {chat_history_table_name}
        WHERE user_id = ? 
        AND strftime('%Y', datetime(timestamp, '+5 hours', '+30 minutes')) = ?
        AND role = 'user'
        GROUP BY day_of_year
        ORDER BY day_of_year
        """,
        (user_id, str(year)),
        fetch_all=True,
    )

    # Convert to dictionary mapping day of year to message count
    activity_map = {int(day) - 1: count for day, count in activity_per_day}

    num_days = 366 if not year % 4 else 365

    data = [activity_map.get(index, 0) for index in range(num_days)]

    return data


def get_user_streak(user_id: int, cohort_id: int):
    user_usage_dates = execute_db_operation(
        f"""
    SELECT MAX(datetime(timestamp, '+5 hours', '+30 minutes')) as timestamp
    FROM {chat_history_table_name}
    WHERE user_id = ? AND task_id IN (SELECT task_id FROM {course_tasks_table_name} WHERE course_id IN (SELECT course_id FROM {course_cohorts_table_name} WHERE cohort_id = ?))
    GROUP BY DATE(datetime(timestamp, '+5 hours', '+30 minutes'))
    ORDER BY timestamp DESC
    """,
        (user_id, cohort_id),
        fetch_all=True,
    )

    return get_user_streak_from_usage_dates(
        [date_str for date_str, in user_usage_dates]
    )


def get_streaks(
    view: LeaderboardViewType = LeaderboardViewType.ALL_TIME, cohort_id: int = None
):
    # Build date filter based on duration
    date_filter = ""
    if view == LeaderboardViewType.WEEKLY:
        date_filter = "AND DATE(datetime(timestamp, '+5 hours', '+30 minutes')) > DATE('now', 'weekday 0', '-7 days')"
    elif view == LeaderboardViewType.MONTHLY:
        date_filter = "AND strftime('%Y-%m', datetime(timestamp, '+5 hours', '+30 minutes')) = strftime('%Y-%m', 'now')"

    # Get all user interactions, ordered by user and timestamp
    usage_per_user = execute_db_operation(
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
        fetch_all=True,
    )

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
    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            # Delete existing tests for the task
            cursor.execute(
                f"DELETE FROM {tests_table_name} WHERE task_id = ?",
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


def delete_all_tests():
    execute_db_operation(f"DELETE FROM {tests_table_name}")


def drop_tests_table():
    execute_db_operation(f"DROP TABLE IF EXISTS {tests_table_name}")


def drop_users_table():
    execute_db_operation(f"DELETE FROM {users_table_name}")
    execute_db_operation(f"DROP TABLE IF EXISTS {users_table_name}")


def delete_all_cohort_info():
    execute_db_operation(f"DELETE FROM {user_groups_table_name}")
    execute_db_operation(f"DELETE FROM {groups_table_name}")
    execute_db_operation(f"DELETE FROM {cohorts_table_name}")


def delete_cohort(cohort_id: int):
    execute_db_operation(
        f"DELETE FROM {user_groups_table_name} WHERE group_id IN (SELECT id FROM {groups_table_name} WHERE cohort_id = ?)",
        (cohort_id,),
    )
    execute_db_operation(
        f"DELETE FROM {groups_table_name} WHERE cohort_id = ?",
        (cohort_id,),
    )
    execute_db_operation(
        f"DELETE FROM {user_cohorts_table_name} WHERE cohort_id = ?",
        (cohort_id,),
    )
    execute_db_operation(
        f"DELETE FROM {cohorts_table_name} WHERE id = ?",
        (cohort_id,),
    )


def drop_cohorts_table():
    execute_db_operation(f"DROP TABLE IF EXISTS {cohorts_table_name}")
    execute_db_operation(f"DROP TABLE IF EXISTS {groups_table_name}")
    execute_db_operation(f"DROP TABLE IF EXISTS {user_groups_table_name}")


def create_cohort(name: str, org_id: int) -> int:
    return execute_db_operation(
        f"""
        INSERT INTO {cohorts_table_name} (name, org_id)
        VALUES (?, ?)
        """,
        params=(name, org_id),
        get_last_row_id=True,
    )


def convert_user_db_to_dict(user: Tuple) -> Dict:
    if not user:
        return

    return {
        "id": user[0],
        "email": user[1],
        "first_name": user[2],
        "middle_name": user[3],
        "last_name": user[4],
        "default_dp_color": user[5],
        "created_at": user[6],
    }


def insert_or_return_user(
    email: str,
    given_name: str = None,
    family_name: str = None,
    conn=None,
    cursor=None,
):
    if given_name is None:
        first_name = None
        middle_name = None
    else:
        given_name_parts = given_name.split(" ")
        first_name = given_name_parts[0]
        middle_name = " ".join(given_name_parts[1:])
        if not middle_name:
            middle_name = None

    is_master_connection = False
    if conn is None:
        conn = get_new_db_connection()
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
            user = convert_user_db_to_dict(user)
            if user["first_name"] is None and first_name:
                user = update_user(
                    user["id"],
                    first_name,
                    middle_name,
                    family_name,
                    user["default_dp_color"],
                )

            return user

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


def add_members_to_cohort(cohort_id: int, emails: List[str], roles: List[str]):
    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            users_to_add = []
            for email in emails:
                # Get or create user
                user = insert_or_return_user(email, conn=conn, cursor=cursor)
                users_to_add.append(user["id"])

            # Add users to cohort
            cursor.executemany(
                f"""
                INSERT INTO {user_cohorts_table_name} (user_id, cohort_id, role)
                VALUES (?, ?, ?)
                """,
                [
                    (user_id, cohort_id, role)
                    for user_id, role in zip(users_to_add, roles)
                ],
            )
            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e


def update_cohort_group_name(group_id: int, new_name: str):
    execute_db_operation(
        f"UPDATE {groups_table_name} SET name = ? WHERE id = ?",
        params=(new_name, group_id),
    )


def add_members_to_cohort_group(
    group_id: int, member_ids: List[int], conn=None, cursor=None
):
    is_master_connection = False
    if conn is None:
        conn = get_new_db_connection()
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
    execute_db_operation(
        f"DELETE FROM {user_groups_table_name} WHERE group_id = ? AND user_id IN ({','.join(['?' for _ in member_ids])})",
        params=(group_id, *member_ids),
    )


def create_cohort_group(name: str, cohort_id: int, member_ids: List[int]):
    with get_shared_db_connection() as conn:
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

            add_members_to_cohort_group(group_id, member_ids, conn=conn, cursor=cursor)

            conn.commit()
            return group_id

        except Exception as e:
            conn.rollback()
            raise e


def delete_cohort_group_from_db(group_id: int):
    execute_multiple_db_operations(
        [
            (f"DELETE FROM {user_groups_table_name} WHERE group_id = ?", (group_id,)),
            (f"DELETE FROM {groups_table_name} WHERE id = ?", (group_id,)),
        ]
    )


def remove_members_from_cohort(cohort_id: int, member_ids: List[int]):
    execute_multiple_db_operations(
        [
            (
                f"""
            DELETE FROM {user_groups_table_name} 
            WHERE user_id IN ({','.join(['?' for _ in member_ids])})
            AND group_id IN (
                SELECT id FROM {groups_table_name} 
                WHERE cohort_id = ?
            )
            """,
                (*member_ids, cohort_id),
            ),
            (
                f"""
            DELETE FROM {user_cohorts_table_name}
            WHERE user_id IN ({','.join(['?' for _ in member_ids])})
            AND cohort_id = ?
            """,
                (*member_ids, cohort_id),
            ),
        ]
    )


def get_all_cohorts_for_org(org_id: int):
    cohorts = execute_db_operation(
        f"""
        SELECT c.id, c.name
        FROM {cohorts_table_name} c
        WHERE c.org_id = ?
        ORDER BY c.id DESC
        """,
        (org_id,),
        fetch_all=True,
    )

    return [{"id": row[0], "name": row[1]} for row in cohorts]


def get_cohort_by_id(cohort_id: int):
    # Fetch cohort details
    cohort = execute_db_operation(
        f"""SELECT * FROM {cohorts_table_name} WHERE id = ?""",
        (cohort_id,),
        fetch_one=True,
    )

    if not cohort:
        return None

    try:
        # Get groups and their members
        groups = execute_db_operation(
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
            fetch_all=True,
        )

        # Get all users and their roles in the cohort
        members = execute_db_operation(
            f"""
            SELECT DISTINCT u.id, u.email, uc.role
            FROM {users_table_name} u
            JOIN {user_cohorts_table_name} uc ON u.id = uc.user_id 
            WHERE uc.cohort_id = ?
            ORDER BY uc.role
            """,
            (cohort_id,),
            fetch_all=True,
        )

        cohort_data = {
            "id": cohort[0],
            "org_id": cohort[2],
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


def is_user_in_cohort(user_id: int, cohort_id: int):
    return execute_db_operation(
        f"""
        SELECT COUNT(*) > 0 FROM (
            SELECT 1
            FROM {user_cohorts_table_name} uc
            WHERE uc.user_id = ? AND uc.cohort_id = ?
            UNION
            SELECT 1 
            FROM {cohorts_table_name} c
            JOIN {organizations_table_name} o ON o.id = c.org_id
            JOIN {user_organizations_table_name} ou ON ou.org_id = o.id
            WHERE c.id = ? AND ou.user_id = ? AND ou.role IN ('admin', 'owner')
        )
        """,
        (user_id, cohort_id, cohort_id, user_id),
        fetch_one=True,
    )[0]


def delete_user_from_cohort(user_id: int, cohort_id: int):
    commands = [
        (
            f"DELETE FROM {user_groups_table_name} WHERE user_id = ? AND group_id IN (SELECT id FROM {groups_table_name} WHERE cohort_id = ?)",
            (user_id, cohort_id),
        ),
        (
            f"DELETE FROM {user_cohorts_table_name} WHERE user_id = ? AND cohort_id = ?",
            (user_id, cohort_id),
        ),
    ]
    execute_multiple_db_operations(commands)


def format_user_cohort_group(group: Tuple):
    learners = []
    for id, email in zip(group[2].split(","), group[3].split(",")):
        learners.append({"id": int(id), "email": email})

    return {
        "id": group[0],
        "name": group[1],
        "learners": learners,
    }


@st.cache_data
def get_mentor_cohort_groups(user_id: int, cohort_id: int):
    groups = execute_db_operation(
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
        params=(user_id, cohort_id),
        fetch_all=True,
    )

    return [format_user_cohort_group(group) for group in groups]


def get_cohort_group_ids_for_users(user_ids: List[int], cohort_id: int):
    groups = execute_db_operation(
        f"""
        SELECT g.id
        FROM {groups_table_name} g
        JOIN {user_groups_table_name} ug ON ug.group_id = g.id
        JOIN {users_table_name} u ON u.id = ug.user_id
        WHERE g.cohort_id = ? AND ug.user_id IN ({','.join(['?' for _ in user_ids])})
        GROUP BY g.id, g.name
        """,
        params=(cohort_id, *user_ids),
        fetch_all=True,
    )
    return [group[0] for group in groups]


def convert_milestone_db_to_dict(milestone: Tuple) -> Dict:
    return {"id": milestone[0], "name": milestone[1], "color": milestone[2]}


def get_all_milestones():
    milestones = execute_db_operation(
        f"SELECT id, name, color FROM {milestones_table_name}", fetch_all=True
    )

    return [convert_milestone_db_to_dict(milestone) for milestone in milestones]


def get_all_milestones_for_org(org_id: int):
    milestones = execute_db_operation(
        f"SELECT id, name, color FROM {milestones_table_name} WHERE org_id = ?",
        (org_id,),
        fetch_all=True,
    )

    return [convert_milestone_db_to_dict(milestone) for milestone in milestones]


def insert_milestone(name: str, color: str, org_id: int):
    execute_db_operation(
        f"INSERT INTO {milestones_table_name} (name, color, org_id) VALUES (?, ?, ?)",
        (name, color, org_id),
    )


def update_milestone(milestone_id: int, name: str, color: str):
    execute_db_operation(
        f"UPDATE {milestones_table_name} SET name = ?, color = ? WHERE id = ?",
        (name, color, milestone_id),
    )


def delete_milestone(milestone_id: int):
    execute_db_operation(
        f"DELETE FROM {milestones_table_name} WHERE id = ?",
        (milestone_id,),
    )


def get_user_metrics_for_all_milestones(user_id: int, course_id: int):
    # Get milestones with tasks
    base_results = execute_db_operation(
        f"""
        SELECT 
            m.id AS milestone_id,
            m.name AS milestone_name,
            m.color AS milestone_color,
            COUNT(DISTINCT t.id) AS total_tasks,
            (
                SELECT COUNT(DISTINCT ch.task_id)
                FROM {chat_history_table_name} ch
                WHERE ch.user_id = ?
                AND ch.is_solved = 1
                AND ch.task_id IN (
                    SELECT t2.id 
                    FROM {tasks_table_name} t2 
                    JOIN {course_tasks_table_name} ct2 ON t2.id = ct2.task_id
                    WHERE t2.milestone_id = m.id 
                    AND ct2.course_id = ?
                    AND t2.deleted_at IS NULL
                )
            ) AS completed_tasks
        FROM 
            {milestones_table_name} m
        LEFT JOIN 
            {tasks_table_name} t ON m.id = t.milestone_id
        LEFT JOIN
            {course_tasks_table_name} ct ON t.id = ct.task_id
        WHERE 
            t.verified = 1 AND ct.course_id = ? AND t.deleted_at IS NULL
        GROUP BY 
            m.id, m.name, m.color
        HAVING 
            COUNT(DISTINCT t.id) > 0
        ORDER BY 
            ct.ordering
        """,
        params=(user_id, course_id, course_id),
        fetch_all=True,
    )

    # Get tasks with null milestone_id
    null_milestone_results = execute_db_operation(
        f"""
        SELECT 
            NULL AS milestone_id,
            '{uncategorized_milestone_name}' AS milestone_name,
            '{uncategorized_milestone_color}' AS milestone_color,
            COUNT(DISTINCT t.id) AS total_tasks,
            (
                SELECT COUNT(DISTINCT ch.task_id)
                FROM {chat_history_table_name} ch
                WHERE ch.user_id = ?
                AND ch.is_solved = 1
                AND ch.task_id IN (
                    SELECT t2.id 
                    FROM {tasks_table_name} t2 
                    JOIN {course_tasks_table_name} ct2 ON t2.id = ct2.task_id
                    WHERE t2.milestone_id IS NULL 
                    AND ct2.course_id = ?
                    AND t2.deleted_at IS NULL
                )
            ) AS completed_tasks
        FROM 
            {tasks_table_name} t
        LEFT JOIN
            {course_tasks_table_name} ct ON t.id = ct.task_id
        WHERE 
            t.milestone_id IS NULL 
            AND t.verified = 1 
            AND t.deleted_at IS NULL
            AND ct.course_id = ?
        HAVING
            COUNT(DISTINCT t.id) > 0
        ORDER BY 
            ct.ordering
        """,
        params=(user_id, course_id, course_id),
        fetch_all=True,
    )

    results = base_results + null_milestone_results

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


def get_cohort_metrics_for_milestone(milestone_task_ids: List[int], cohort_id: int):
    results = execute_db_operation(
        f"""
        WITH cohort_learners AS (
            SELECT u.id, u.email
            FROM {users_table_name} u
            JOIN {user_cohorts_table_name} uc ON u.id = uc.user_id 
            WHERE uc.cohort_id = ? AND uc.role = 'learner'
        ),
        task_completion AS (
            SELECT 
                cl.id as user_id,
                cl.email,
                ch.task_id,
                MAX(COALESCE(ch.is_solved, 0)) as is_solved
            FROM cohort_learners cl
            LEFT JOIN {chat_history_table_name} ch 
                ON cl.id = ch.user_id 
                AND ch.task_id IN ({','.join('?' * len(milestone_task_ids))})
            LEFT JOIN {tasks_table_name} t
                ON ch.task_id = t.id
            GROUP BY cl.id, cl.email, ch.task_id, t.name
        )
        SELECT 
            user_id,
            email,
            GROUP_CONCAT(task_id) as task_ids,
            GROUP_CONCAT(is_solved) as task_completion
        FROM task_completion
        GROUP BY user_id, email
        """,
        (cohort_id, *milestone_task_ids),
        fetch_all=True,
    )

    user_metrics = []
    task_metrics = defaultdict(list)
    for row in results:
        task_completions = [
            int(x) if x else 0 for x in (row[3].split(",") if row[3] else [])
        ]
        task_ids = list(map(int, row[2].split(","))) if row[2] else []

        for task_id, task_completion in zip(task_ids, task_completions):
            task_metrics[task_id].append(task_completion)

        for task_id in milestone_task_ids:
            if task_id in task_ids:
                continue

            task_metrics[task_id].append(0)

        num_completed = sum(task_completions)

        user_metrics.append(
            {
                "user_id": row[0],
                "email": row[1],
                "num_completed": num_completed,
            }
        )

    task_metrics = {task_id: task_metrics[task_id] for task_id in milestone_task_ids}

    for index, row in enumerate(user_metrics):
        for task_id in milestone_task_ids:
            row[f"task_{task_id}"] = task_metrics[task_id][index]

    return user_metrics


def update_user(
    user_id: str,
    first_name: str,
    middle_name: str,
    last_name: str,
    default_dp_color: str,
):
    execute_db_operation(
        f"UPDATE {users_table_name} SET first_name = ?, middle_name = ?, last_name = ?, default_dp_color = ? WHERE id = ?",
        params=(first_name, middle_name, last_name, default_dp_color, user_id),
    )

    user = get_user_by_id(user_id)
    return user


def get_all_users():
    users = execute_db_operation(
        f"SELECT * FROM {users_table_name}",
        fetch_all=True,
    )

    return [convert_user_db_to_dict(user) for user in users]


def get_user_by_email(email: str) -> Dict:
    user = execute_db_operation(
        f"SELECT * FROM {users_table_name} WHERE email = ?", (email,), fetch_one=True
    )

    return convert_user_db_to_dict(user)


def get_user_by_id(user_id: str) -> Dict:
    user = execute_db_operation(
        f"SELECT * FROM {users_table_name} WHERE id = ?", (user_id,), fetch_one=True
    )

    return convert_user_db_to_dict(user)


def get_user_cohorts(user_id: int) -> List[Dict]:
    """Get all cohorts (and the groups in each cohort) that the user is a part of along with their role in each group"""
    results = execute_db_operation(
        f"""
        SELECT c.id, c.name, uc.role, o.id, o.name
        FROM {cohorts_table_name} c
        JOIN {user_cohorts_table_name} uc ON uc.cohort_id = c.id
        JOIN {organizations_table_name} o ON o.id = c.org_id
        WHERE uc.user_id = ?
        """,
        (user_id,),
        fetch_all=True,
    )

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
    results = execute_db_operation(
        f"""
        SELECT c.id, c.name, o.id, o.name
        FROM {cohorts_table_name} c
        JOIN {organizations_table_name} o ON o.id = c.org_id
        WHERE o.id = ?
        """,
        (org_id,),
        fetch_all=True,
    )

    # Convert results into nested dict structure
    return [
        {"id": cohort_id, "name": cohort_name, "org_id": org_id, "org_name": org_name}
        for cohort_id, cohort_name, org_id, org_name in results
    ]


def create_badge_for_user(
    user_id: int,
    value: str,
    badge_type: str,
    image_path: str,
    bg_color: str,
    cohort_id: int,
) -> int:
    return execute_db_operation(
        f"INSERT INTO {badges_table_name} (user_id, value, type, image_path, bg_color, cohort_id) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, value, badge_type, image_path, bg_color, cohort_id),
        get_last_row_id=True,
    )


def update_badge(
    badge_id: int, value: str, badge_type: str, image_path: str, bg_color: str
):
    execute_db_operation(
        f"UPDATE {badges_table_name} SET value = ?, type = ?, image_path = ?, bg_color = ? WHERE id = ?",
        (value, badge_type, image_path, bg_color, badge_id),
    )


def convert_badge_db_to_dict(badge: Tuple):
    if badge is None:
        return

    output = {
        "id": badge[0],
        "user_id": badge[1],
        "value": badge[2],
        "type": badge[3],
        "image_path": badge[4],
        "bg_color": badge[5],
    }

    if len(badge) > 6:
        output["cohort_name"] = badge[6]
        output["org_name"] = badge[7]

    return output


def get_badge_by_id(badge_id: int) -> Dict:
    badge = execute_db_operation(
        f"SELECT b.id, b.user_id, b.value, b.type, b.image_path, b.bg_color, c.name, o.name FROM {badges_table_name} b LEFT JOIN {cohorts_table_name} c ON c.id = b.cohort_id LEFT JOIN {organizations_table_name} o ON o.id = c.org_id WHERE b.id = ?",
        (badge_id,),
        fetch_one=True,
    )

    return convert_badge_db_to_dict(badge)


def get_badges_by_user_id(user_id: int) -> List[Dict]:
    badges = execute_db_operation(
        f"SELECT b.id, b.user_id, b.value, b.type, b.image_path, b.bg_color, c.name, o.name FROM {badges_table_name} b LEFT JOIN {cohorts_table_name} c ON c.id = b.cohort_id LEFT JOIN {organizations_table_name} o ON o.id = c.org_id WHERE b.user_id = ? ORDER BY b.id DESC",
        (user_id,),
        fetch_all=True,
    )

    return [convert_badge_db_to_dict(badge) for badge in badges]


def get_cohort_badge_by_type_and_user_id(
    user_id: int, badge_type: str, cohort_id: int
) -> Dict:
    badge = execute_db_operation(
        f"SELECT id, user_id, value, type, image_path, bg_color FROM {badges_table_name} WHERE user_id = ? AND type = ? AND cohort_id = ?",
        (user_id, badge_type, cohort_id),
        fetch_one=True,
    )

    return convert_badge_db_to_dict(badge)


def delete_badge_by_id(badge_id: int):
    execute_db_operation(
        f"DELETE FROM {badges_table_name} WHERE id = ?",
        (badge_id,),
    )


def clear_badges_table():
    execute_db_operation(f"DELETE FROM {badges_table_name}")


def drop_badges_table():
    execute_multiple_db_operations(
        [
            (f"DELETE FROM {badges_table_name}", ()),
            (f"DROP TABLE IF EXISTS {badges_table_name}", ()),
        ]
    )


def add_cv_review_usage(user_id: int, role: str, ai_review: str):
    execute_db_operation(
        f"INSERT INTO {cv_review_usage_table_name} (user_id, role, ai_review) VALUES (?, ?, ?)",
        (user_id, role, ai_review),
    )


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
    execute_multiple_db_operations(
        [
            (f"DELETE FROM {cv_review_usage_table_name}", ()),
            (f"DROP TABLE IF EXISTS {cv_review_usage_table_name}", ()),
        ]
    )


def get_all_cv_review_usage():
    all_cv_review_usage = execute_db_operation(
        f"""
        SELECT cv.id, cv.user_id, u.email, cv.role, cv.ai_review , cv.created_at
        FROM {cv_review_usage_table_name} cv
        JOIN users u ON cv.user_id = u.id
        """,
        fetch_all=True,
    )

    return [
        transform_cv_review_usage_to_dict(cv_review_usage)
        for cv_review_usage in all_cv_review_usage
    ]


def drop_user_organizations_table():
    execute_multiple_db_operations(
        [
            (f"DELETE FROM {user_organizations_table_name}", ()),
            (f"DROP TABLE IF EXISTS {user_organizations_table_name}", ()),
        ]
    )


def drop_organizations_table():
    drop_user_organizations_table()

    execute_multiple_db_operations(
        [
            (f"DELETE FROM {organizations_table_name}", ()),
            (f"DROP TABLE IF EXISTS {organizations_table_name}", ()),
        ]
    )


def create_organization(name: str, color: str = None, conn=None, cursor=None):
    slug = slugify(name) + "-" + str(uuid.uuid4())
    default_logo_color = color or generate_random_color()

    is_master_connection = False
    if conn is None:
        conn = get_new_db_connection()
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


def update_org(org_id: int, org_name: str):
    execute_db_operation(
        f"UPDATE {organizations_table_name} SET name = ? WHERE id = ?",
        (org_name, org_id),
    )


def update_org_openai_api_key(org_id: int, openai_api_key: str):
    encrypted_openai_api_key = encrypt_openai_api_key(openai_api_key)

    execute_db_operation(
        f"UPDATE {organizations_table_name} SET openai_api_key = ? WHERE id = ?",
        (encrypted_openai_api_key, org_id),
    )


def clear_org_openai_api_key(org_id: int):
    execute_db_operation(
        f"UPDATE {organizations_table_name} SET openai_api_key = NULL WHERE id = ?",
        (org_id,),
    )


def add_user_to_org_by_user_id(
    user_id: int,
    org_id: int,
    role: Literal["owner", "admin"],
    conn=None,
    cursor=None,
):
    is_master_connection = False
    if conn is None:
        conn = get_new_db_connection()
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


def create_organization_with_user(
    org_name: str, user_id: int, color: str = None, conn=None, cursor=None
):
    org_id = create_organization(org_name, color, conn=conn, cursor=cursor)
    add_user_to_org_by_user_id(user_id, org_id, "owner", conn=conn, cursor=cursor)
    return org_id


def convert_org_db_to_dict(org: Tuple):
    if not org:
        return None

    return {
        "id": org[0],
        "slug": org[1],
        "name": org[2],
        "logo_color": org[3],
        "openai_api_key": org[5],
    }


def get_org_by_id(org_id: int):
    org_details = execute_db_operation(
        f"SELECT * FROM {organizations_table_name} WHERE id = ?",
        (org_id,),
        fetch_one=True,
    )

    return convert_org_db_to_dict(org_details)


def get_hva_org_id():
    if "hva_org_id" in st.session_state:
        return st.session_state.hva_org_id

    hva_org_id = execute_db_operation(
        "SELECT id FROM organizations WHERE name = ?",
        ("HyperVerge Academy",),
        fetch_one=True,
    )[0]

    st.session_state.hva_org_id = hva_org_id
    return hva_org_id


def get_hva_cohort_ids() -> List[int]:
    cohorts = execute_db_operation(
        "SELECT id FROM cohorts WHERE org_id = ?",
        (get_hva_org_id(),),
        fetch_all=True,
    )
    return [cohort[0] for cohort in cohorts]


def is_user_hva_learner(user_id: int) -> bool:
    return (
        execute_db_operation(
            f"SELECT COUNT(*) FROM user_cohorts WHERE user_id = ? AND cohort_id IN ({', '.join(map(str, get_hva_cohort_ids()))})",
            (user_id,),
            fetch_one=True,
        )[0]
        > 0
    )


def get_hva_openai_api_key() -> str:
    return get_org_by_id(get_hva_org_id())["openai_api_key"]


def add_user_to_org_by_email(
    email: str,
    org_id: int,
    role: Literal["owner", "admin"],
):
    with get_shared_db_connection() as conn:
        cursor = conn.cursor()
        try:
            user = insert_or_return_user(email, conn=conn, cursor=cursor)

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


def remove_members_from_org(org_id: int, user_ids: List[int]):
    execute_db_operation(
        f"DELETE FROM {user_organizations_table_name} WHERE org_id = ? AND user_id IN ({', '.join(map(str, user_ids))})",
        (org_id,),
    )


def convert_user_organization_db_to_dict(user_organization: Tuple):
    return {
        "id": user_organization[0],
        "user_id": user_organization[1],
        "org_id": user_organization[2],
        "role": user_organization[3],
    }


def get_user_organizations(user_id: int):
    user_organizations = execute_db_operation(
        f"""SELECT uo.org_id, o.name, uo.role, o.openai_api_key
        FROM {user_organizations_table_name} uo
        JOIN organizations o ON uo.org_id = o.id 
        WHERE uo.user_id = ? ORDER BY uo.id DESC""",
        (user_id,),
        fetch_all=True,
    )

    return [
        {
            "id": user_organization[0],
            "name": user_organization[1],
            "role": user_organization[2],
            "openai_api_key": user_organization[3],
        }
        for user_organization in user_organizations
    ]


def get_org_users(org_id: int):
    org_users = execute_db_operation(
        f"""SELECT uo.user_id, u.email, uo.role 
        FROM {user_organizations_table_name} uo
        JOIN users u ON uo.user_id = u.id 
        WHERE uo.org_id = ?""",
        (org_id,),
        fetch_all=True,
    )

    return [
        {
            "id": org_user[0],
            "email": org_user[1],
            "role": org_user[2],
        }
        for org_user in org_users
    ]


def get_all_user_organizations():
    user_organizations = execute_db_operation(
        f"SELECT * FROM {user_organizations_table_name}", fetch_all=True
    )

    return [
        convert_user_organization_db_to_dict(user_organization)
        for user_organization in user_organizations
    ]


def drop_task_tags_table():
    commands = [
        (f"DELETE FROM {task_tags_table_name}", ()),
        (f"DROP TABLE IF EXISTS {task_tags_table_name}", ()),
    ]
    execute_multiple_db_operations(commands)


def drop_tags_table():
    drop_task_tags_table()

    commands = [
        (f"DELETE FROM {tags_table_name}", ()),
        (f"DROP TABLE IF EXISTS {tags_table_name}", ()),
    ]
    execute_multiple_db_operations(commands)


def create_tag(tag_name: str, org_id: int):
    execute_db_operation(
        f"INSERT INTO {tags_table_name} (name, org_id) VALUES (?, ?)",
        (tag_name, org_id),
    )


def create_bulk_tags(tag_names: List[str], org_id: int) -> bool:
    if not tag_names:
        return False

    with get_shared_db_connection() as conn:
        cursor = conn.cursor()

        # Get existing tags
        cursor.execute(
            f"SELECT name FROM {tags_table_name} WHERE org_id = ?", (org_id,)
        )
        existing_tags = {row[0] for row in cursor.fetchall()}

        # Filter out tags that already exist
        new_tags = [tag for tag in tag_names if tag not in existing_tags]

        has_new_tags = len(new_tags) > 0

        # Insert new tags
        if new_tags:
            try:
                cursor.executemany(
                    f"INSERT INTO {tags_table_name} (name, org_id) VALUES (?, ?)",
                    [(tag, org_id) for tag in new_tags],
                )

                conn.commit()
                return has_new_tags
            except Exception as e:
                conn.rollback()
                raise e


def convert_tag_db_to_dict(tag: Tuple) -> Dict:
    return {
        "id": tag[0],
        "name": tag[1],
        "created_at": convert_utc_to_ist(datetime.fromisoformat(tag[2])).isoformat(),
    }


def get_all_tags() -> List[Dict]:
    tags = execute_db_operation(f"SELECT * FROM {tags_table_name}", fetch_all=True)

    return [convert_tag_db_to_dict(tag) for tag in tags]


def get_all_tags_for_org(org_id: int) -> List[Dict]:
    tags = execute_db_operation(
        f"SELECT * FROM {tags_table_name} WHERE org_id = ?", (org_id,), fetch_all=True
    )

    return [convert_tag_db_to_dict(tag) for tag in tags]


def delete_tag(tag_id: int):
    execute_db_operation(f"DELETE FROM {tags_table_name} WHERE id = ?", (tag_id,))


def transfer_badge_to_user(prev_user_id: int, new_user_id: int):
    execute_db_operation(
        f"UPDATE {badges_table_name} SET user_id = ? WHERE user_id = ?",
        (new_user_id, prev_user_id),
    )


def transfer_chat_history_to_user(prev_user_id: int, new_user_id: int):
    execute_db_operation(
        f"UPDATE {chat_history_table_name} SET user_id = ? WHERE user_id = ?",
        (new_user_id, prev_user_id),
    )


def drop_user_cohorts_table():
    execute_db_operation(f"DROP TABLE IF EXISTS {user_cohorts_table_name}")


def get_courses_for_tasks(task_ids: List[int]):
    results = execute_db_operation(
        f"SELECT ct.task_id, c.id, c.name FROM {course_tasks_table_name} ct JOIN {courses_table_name} c ON ct.course_id = c.id WHERE ct.task_id IN ({', '.join(map(str, task_ids))})",
        fetch_all=True,
    )

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
    with get_shared_db_connection() as conn:
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


def remove_tasks_from_courses(course_tasks_to_remove: List[Tuple[int, int]]):
    execute_many_db_operation(
        f"DELETE FROM {course_tasks_table_name} WHERE task_id = ? AND course_id = ?",
        params_list=course_tasks_to_remove,
    )


def update_task_orders(task_orders: List[Tuple[int, int]]):
    execute_many_db_operation(
        f"UPDATE {course_tasks_table_name} SET ordering = ? WHERE id = ?",
        params_list=task_orders,
    )


def add_scoring_criteria_to_task(task_id: int, scoring_criteria: List[Dict]):
    if not scoring_criteria:
        return

    execute_many_db_operation(
        f"""INSERT INTO {task_scoring_criteria_table_name} 
            (task_id, category, description, min_score, max_score) 
            VALUES (?, ?, ?, ?, ?)""",
        params_list=[
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


def remove_scoring_criteria_from_task(scoring_criteria_ids: List[int]):
    if not scoring_criteria_ids:
        return

    execute_db_operation(
        f"""DELETE FROM {task_scoring_criteria_table_name} 
            WHERE id IN ({', '.join(map(str, scoring_criteria_ids))})"""
    )


def add_scoring_criteria_to_tasks(task_ids: List[int], scoring_criteria: List[Dict]):
    if not scoring_criteria:
        return

    params = list(
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
    )

    execute_many_db_operation(
        f"""INSERT INTO {task_scoring_criteria_table_name} 
            (task_id, category, description, min_score, max_score) 
            VALUES (?, ?, ?, ?, ?)""",
        params_list=params,
    )


def create_course(name: str, org_id: int) -> int:
    course_id = execute_db_operation(
        f"""
        INSERT INTO {courses_table_name} (name, org_id)
        VALUES (?, ?)
        """,
        (name, org_id),
        get_last_row_id=True,
    )
    return course_id


def update_course_name(course_id: int, name: str):
    execute_db_operation(
        f"UPDATE {courses_table_name} SET name = ? WHERE id = ?",
        (name, course_id),
    )


def update_cohort_name(cohort_id: int, name: str):
    execute_db_operation(
        f"UPDATE {cohorts_table_name} SET name = ? WHERE id = ?",
        (name, cohort_id),
    )


def convert_course_db_to_dict(course: Tuple) -> Dict:
    return {
        "id": course[0],
        "name": course[1],
    }


def get_all_courses_for_org(org_id: int):
    courses = execute_db_operation(
        f"SELECT id, name FROM {courses_table_name} WHERE org_id = ? ORDER BY id DESC",
        (org_id,),
        fetch_all=True,
    )

    return [convert_course_db_to_dict(course) for course in courses]


def delete_course(course_id: int):
    execute_multiple_db_operations(
        [
            (
                f"DELETE FROM {course_cohorts_table_name} WHERE course_id = ?",
                (course_id,),
            ),
            (f"DELETE FROM {courses_table_name} WHERE id = ?", (course_id,)),
        ]
    )


def delete_all_courses_for_org(org_id: int):
    execute_multiple_db_operations(
        [
            (
                f"DELETE FROM {course_cohorts_table_name} WHERE course_id IN (SELECT id FROM {courses_table_name} WHERE org_id = ?)",
                (org_id,),
            ),
            (f"DELETE FROM {courses_table_name} WHERE org_id = ?", (org_id,)),
        ]
    )


def add_course_to_cohorts(course_id: int, cohort_ids: List[int]):
    execute_many_db_operation(
        f"INSERT INTO {course_cohorts_table_name} (course_id, cohort_id) VALUES (?, ?)",
        [(course_id, cohort_id) for cohort_id in cohort_ids],
    )


def add_courses_to_cohort(cohort_id: int, course_ids: List[int]):
    execute_many_db_operation(
        f"INSERT INTO {course_cohorts_table_name} (course_id, cohort_id) VALUES (?, ?)",
        [(course_id, cohort_id) for course_id in course_ids],
    )


def remove_course_from_cohorts(course_id: int, cohort_ids: List[int]):
    execute_many_db_operation(
        f"DELETE FROM {course_cohorts_table_name} WHERE course_id = ? AND cohort_id = ?",
        [(course_id, cohort_id) for cohort_id in cohort_ids],
    )


def remove_courses_from_cohort(cohort_id: int, course_ids: List[int]):
    execute_many_db_operation(
        f"DELETE FROM {course_cohorts_table_name} WHERE cohort_id = ? AND course_id = ?",
        [(cohort_id, course_id) for course_id in course_ids],
    )


@st.cache_data
def get_courses_for_cohort(cohort_id: int):
    courses = execute_db_operation(
        f"""
        SELECT c.id, c.name 
        FROM {courses_table_name} c
        JOIN {course_cohorts_table_name} cc ON c.id = cc.course_id
        WHERE cc.cohort_id = ?
        """,
        (cohort_id,),
        fetch_all=True,
    )
    return [{"id": course[0], "name": course[1]} for course in courses]


@st.cache_data
def get_cohorts_for_course(course_id: int):
    cohorts = execute_db_operation(
        f"""
        SELECT ch.id, ch.name 
        FROM {cohorts_table_name} ch
        JOIN {course_cohorts_table_name} cc ON ch.id = cc.cohort_id
        WHERE cc.course_id = ?
        """,
        (course_id,),
        fetch_all=True,
    )

    return [{"id": cohort[0], "name": cohort[1]} for cohort in cohorts]


def drop_course_cohorts_table():
    execute_multiple_db_operations(
        [
            (f"DELETE FROM {course_cohorts_table_name}", ()),
            (f"DROP TABLE IF EXISTS {course_cohorts_table_name}", ()),
        ]
    )


def drop_courses_table():
    drop_course_cohorts_table()

    execute_multiple_db_operations(
        [
            (f"DELETE FROM {courses_table_name}", ()),
            (f"DROP TABLE IF EXISTS {courses_table_name}", ()),
        ]
    )


def get_tasks_for_course(course_id: int, milestone_id: int = None):
    query = f"""SELECT t.id, t.name, COALESCE(m.name, '{uncategorized_milestone_name}') as milestone_name, t.verified, t.input_type, t.response_type, t.coding_language, ct.ordering, ct.id as course_task_id, t.milestone_id, t.type
        FROM {course_tasks_table_name} ct 
        JOIN {tasks_table_name} t ON ct.task_id = t.id 
        LEFT JOIN {milestones_table_name} m ON t.milestone_id = m.id
        WHERE ct.course_id = ? AND t.deleted_at IS NULL
        """

    params = [course_id]

    if milestone_id is not None:
        query += " AND t.milestone_id = ?"
        params.append(milestone_id)

    query += " ORDER BY ct.ordering"

    tasks = execute_db_operation(query, tuple(params), fetch_all=True)

    return [
        {
            "id": task[0],
            "name": task[1],
            "milestone": task[2],
            "verified": task[3],
            "input_type": task[4],
            "response_type": task[5],
            "coding_language": deserialise_list_from_str(task[6]),
            "ordering": task[7],
            "course_task_id": task[8],
            "milestone_id": task[9],
            "type": task[10],
        }
        for task in tasks
    ]


def migrate_tasks_table():
    conn = get_new_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({tasks_table_name})")
    columns = cursor.fetchall()

    try:
        if not any(column[1] == "input_type" for column in columns):
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {tasks_table_name}_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    answer TEXT,
                    input_type TEXT ,
                    coding_language TEXT,
                    generation_model TEXT,
                    verified BOOLEAN NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    milestone_id INTEGER,
                    org_id INTEGER NOT NULL,
                    response_type TEXT,
                    context TEXT,
                    deleted_at DATETIME,
                    type TEXT NOT NULL,
                    FOREIGN KEY (milestone_id) REFERENCES {milestones_table_name}(id),
                    FOREIGN KEY (org_id) REFERENCES {organizations_table_name}(id)
                )"""
            )
            cursor.execute(
                f"""
                INSERT INTO {tasks_table_name}_new 
                (
                    id, name, description, answer, input_type, coding_language, generation_model, 
                    verified, timestamp, milestone_id, org_id, response_type, context, deleted_at, type
                )
                SELECT 
                    id, 
                    name, 
                    description, 
                    answer, 
                    type as input_type, 
                    coding_language, 
                    generation_model, 
                    verified, 
                    timestamp, 
                    milestone_id, 
                    org_id, 
                    response_type, 
                    context, 
                    deleted_at,
                    CASE 
                        WHEN type = 'NA' THEN 'reading_material'
                        ELSE 'question'
                    END AS type 
                FROM {tasks_table_name}
            """
            )
            cursor.execute(f"DROP TABLE {tasks_table_name}")
            cursor.execute(
                f"ALTER TABLE {tasks_table_name}_new RENAME TO {tasks_table_name}"
            )

        conn.commit()
    except Exception as e:
        print(f"Error adding deleted_at column to tasks table: {e}")
        conn.rollback()
    finally:
        conn.close()


def migrate_chat_history_table():
    conn = get_shared_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {chat_history_table_name}_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                is_solved BOOLEAN NOT NULL DEFAULT 0,
                response_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )"""
        )
        cursor.execute(
            f"""
            INSERT INTO {chat_history_table_name}_new
            (
                id, user_id, task_id, role, content, is_solved, response_type, timestamp
            )
            SELECT 
                id, 
                user_id, 
                task_id, 
                role, 
                content, 
                is_solved, 
                response_type, 
                timestamp
            FROM {chat_history_table_name}
        """
        )
        cursor.execute(f"DROP TABLE {chat_history_table_name}")
        cursor.execute(
            f"ALTER TABLE {chat_history_table_name}_new RENAME TO {chat_history_table_name}"
        )

        conn.commit()
    except Exception as e:
        print(f"Error migrating chat history table: {e}")
        conn.rollback()
    finally:
        conn.close()


def migrate_org_table():
    conn = get_new_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"ALTER TABLE {organizations_table_name} ADD COLUMN openai_api_key TEXT"
    )
    conn.commit()
    conn.close()


def seed_openai_api_key():
    conn = get_new_db_connection()
    cursor = conn.cursor()

    try:
        hva_org_id = get_hva_org_id()
        openai_api_key = os.getenv("OPENAI_API_KEY")

        print(openai_api_key)
        print(hva_org_id)

        if openai_api_key:
            encrypted_key = encrypt_openai_api_key(openai_api_key)
            cursor.execute(
                f"UPDATE {organizations_table_name} SET openai_api_key = ? WHERE id = ?",
                (encrypted_key, hva_org_id),
            )
            print("done")
            conn.commit()
    except Exception as e:
        print(f"Error seeding OpenAI API key: {e}")
        conn.rollback()
    finally:
        conn.close()
