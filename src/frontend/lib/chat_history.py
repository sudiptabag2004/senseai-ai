import os
import json
import requests
from typing import List, Dict
from datetime import datetime


def get_all_chat_history(org_id: int) -> List[Dict]:
    """Get all chat history for an organization"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/chat", params={"org_id": org_id}
    )
    if response.status_code != 200:
        raise Exception("Failed to get chat history")
    return response.json()


def get_task_chat_history_for_user(task_id: int, user_id: int) -> List[Dict]:
    """Get chat history for a specific task and user"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/chat/task/{task_id}/user/{user_id}"
    )
    if response.status_code != 200:
        raise Exception("Failed to get task chat history")
    return response.json()


def get_user_chat_history_for_tasks(task_ids: List[int], user_id: int) -> List[Dict]:
    """Get chat history for multiple tasks and a user"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/chat/user/{user_id}/tasks",
        params={"task_ids": task_ids},
    )
    if response.status_code != 200:
        raise Exception("Failed to get user chat history for tasks")
    return response.json()


def store_message(
    user_id: int,
    task_id: int,
    role: str,
    content: str,
    is_solved: bool = False,
    response_type: str = None,
) -> Dict:
    """Store a new chat message"""
    payload = json.dumps(
        {
            "user_id": user_id,
            "task_id": task_id,
            "role": role,
            "content": content,
            "is_solved": is_solved,
            "response_type": response_type,
        }
    )
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/chat",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to store message")
    return response.json()
