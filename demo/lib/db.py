

import os
from os.path import exists
import sqlite3
from typing import List
import streamlit as st
from lib.config import sqlite_db_path, chat_history_table_name, tasks_table_name


def init_db():
    if exists(sqlite_db_path):
        # db already exists, so table must already exist
        return

    # Connect to the SQLite database (it will create the database if it doesn't exist)
    conn = sqlite3.connect(sqlite_db_path)

    try:
        # Create a cursor object
        cursor = conn.cursor()

        # Create a table to store tasks
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {tasks_table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            answer TEXT NOT NULL,
            tags TEXT NOT NULL,  -- Stored as comma-separated values
            generation_model TEXT NOT NULL,
            verified BOOLEAN NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create a table to store chat history
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {chat_history_table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES {tasks_table_name}(id)
        )
        ''')

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    except Exception as exception:
        # delete db
        conn.close()
        os.remove(sqlite_db_path)
        raise exception    


# @st.cache_resource
def get_db_connection():
    # print(sqlite_db_path)
    return sqlite3.connect(sqlite_db_path)


def store_task(task_name: str, description: str, answer: str, task_tags: List[str], generation_model: str, verified: bool):
    task_tags_str = ",".join(task_tags)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    INSERT INTO {tasks_table_name} (name, description, answer, tags, generation_model, verified)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (task_name, description, answer, task_tags_str, generation_model, verified))

    conn.commit()
    conn.close()


def get_all_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    SELECT id, name, description, answer, tags, generation_model, verified FROM {tasks_table_name}
    ORDER BY timestamp ASC
    ''')

    tasks = cursor.fetchall()

    tasks_dicts = [
        {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'answer': row[3],
            'tags': row[4].split(','),
            'generation_model': row[5],
            'verified': bool(row[6])
        }
        for row in tasks
    ]

    conn.close()

    return tasks_dicts


def get_task_by_id(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    SELECT id, name, description, answer, tags, generation_model, verified FROM {tasks_table_name} WHERE id = ?
    ''', (task_id,))

    task = cursor.fetchone()

    conn.close()

    if not task:
        return None

    return {
        'id': task[0],
        'name': task[1],
        'description': task[2],
        'answer': task[3],
        'tags': task[4].split(','),
        'generation_model': task[5],
        'verified': bool(task[6])
    }


def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    DELETE FROM {tasks_table_name} WHERE id = ?
    ''', (task_id,))

    conn.commit()
    conn.close()


def delete_tasks(task_ids: List[int]):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    DELETE FROM {tasks_table_name} WHERE id IN ({','.join(task_ids)})
    ''', (task_ids,))

    conn.commit()
    conn.close()


def delete_all_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    DELETE FROM {tasks_table_name}
    ''')

    conn.commit()
    conn.close()


def store_message(user_id: str, task_id: int, role: str, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    INSERT INTO {chat_history_table_name} (user_id, task_id, role, content)
    VALUES (?, ?, ?, ?)
    ''', (user_id, task_id, role, content))

    # Get the ID of the newly inserted row
    new_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Fetch the newly inserted row
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    SELECT id, timestamp, user_id, task_id, role, content
    FROM {chat_history_table_name}
    WHERE id = ?
    ''', (new_id,))

    new_row = cursor.fetchone()

    conn.close()

    # Return the newly inserted row as a dictionary
    return {
        'id': new_row[0],
        'timestamp': new_row[1],
        'user_id': new_row[2],
        'task_id': new_row[3],
        'role': new_row[4],
        'content': new_row[5]
    }


def get_all_chat_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    SELECT message.id, message.timestamp, message.user_id, message.task_id, task.name AS task_name, message.role, message.content 
    FROM {chat_history_table_name} message
    LEFT JOIN {tasks_table_name} task ON message.task_id = task.id
    ORDER BY message.timestamp ASC
    ''')

    chat_history = cursor.fetchall()

    conn.close()

    chat_history_dicts = [
        {
            'id': row[0],
            'timestamp': row[1],
            'user_id': row[2],
            'task_id': row[3],
            'task_name': row[4],
            'role': row[5],
            'content': row[6]
        }
        for row in chat_history
    ]

    return chat_history_dicts


def get_task_chat_history_for_user(task_id: int, user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    SELECT id, timestamp, user_id, task_id, role, content FROM {chat_history_table_name} WHERE task_id = ? AND user_id = ?
    ''', (task_id, user_id))

    chat_history = cursor.fetchall()

    conn.close()

    chat_history_dicts = [
        {
            'id': row[0],
            'timestamp': row[1],
            'user_id': row[2],
            'task_id': row[3],
            'role': row[4],
            'content': row[5]
        }
        for row in chat_history
    ]
    return chat_history_dicts


def delete_message(message_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    DELETE FROM {chat_history_table_name} WHERE id = ?
    ''', (message_id,))

    conn.commit()
    conn.close()


def delete_all_chat_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
    DELETE FROM {chat_history_table_name}
    ''')

    conn.commit()
    conn.close()