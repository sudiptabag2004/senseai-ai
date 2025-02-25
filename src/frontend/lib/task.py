import os
import json
import requests
from typing import List, Dict
from models import LeaderboardViewType


def get_tasks_for_org(org_id: int, return_tests: bool = False) -> List[Dict]:
    """Get all tasks for an organization"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks",
        params={"org_id": org_id, "return_tests": return_tests},
    )
    if response.status_code != 200:
        raise Exception("Failed to get tasks")
    return response.json()


def get_tasks_for_course(course_id: int, milestone_id: int = None) -> List[Dict]:
    """Get all verified tasks for a course"""
    params = {}
    if milestone_id is not None:
        params["milestone_id"] = milestone_id

    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks/course/{course_id}/verified",
        params=params,
    )
    if response.status_code != 200:
        raise Exception("Failed to get verified tasks")
    return response.json()


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
    org_id: int,
    context: str,
    task_type: str,
) -> int:
    """Store a new task"""
    payload = json.dumps(
        {
            "name": name,
            "description": description,
            "answer": answer,
            "tags": tags,
            "input_type": input_type,
            "response_type": response_type,
            "coding_languages": coding_languages,
            "generation_model": generation_model,
            "verified": verified,
            "tests": tests,
            "org_id": org_id,
            "context": context,
            "task_type": task_type,
        }
    )
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/tasks",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to store task")
    return response.json()


def update_task(
    task_id: int,
    name: str,
    description: str,
    answer: str,
    input_type: str,
    response_type: str,
    coding_languages: List[str],
    context: str,
) -> Dict:
    """Update an existing task"""
    payload = json.dumps(
        {
            "name": name,
            "description": description,
            "answer": answer,
            "input_type": input_type,
            "response_type": response_type,
            "coding_languages": coding_languages,
            "context": context,
        }
    )
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/tasks/{task_id}",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to update task")
    return response.json()


def delete_task(task_id: int) -> Dict:
    """Delete a task"""
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/tasks/{task_id}")
    if response.status_code != 200:
        raise Exception("Failed to delete task")
    return response.json()


def delete_tasks(task_ids: List[int]) -> Dict:
    """Delete multiple tasks"""
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/tasks",
        params={"task_ids": task_ids},
    )
    if response.status_code != 200:
        raise Exception("Failed to delete tasks")
    return response.json()


def get_solved_tasks_for_user(
    user_id: int,
    cohort_id: int,
    view: str = str(LeaderboardViewType.ALL_TIME),
) -> List[int]:
    """Get completed tasks for a user"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks/cohort/{cohort_id}/user/{user_id}/completed",
        params={"view": view},
    )
    if response.status_code != 200:
        raise Exception("Failed to get completed tasks")
    return response.json()


def get_task(task_id: int, course_id: int) -> Dict:
    """Get a specific task"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks/{task_id}",
        params={"course_id": course_id},
    )
    if response.status_code != 200:
        raise Exception("Failed to get task")
    return response.json()


def get_scoring_criteria_for_task(task_id: int) -> List[Dict]:
    """Get scoring criteria for a task"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks/{task_id}/scoring_criteria"
    )
    if response.status_code != 200:
        raise Exception("Failed to get task scoring criteria")
    return response.json()


def get_scoring_criteria_for_tasks(task_ids: List[int]) -> List[Dict]:
    """Get scoring criteria for multiple tasks"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks/scoring_criteria",
        params={"task_ids": task_ids},
    )
    if response.status_code != 200:
        raise Exception("Failed to get scoring criteria")
    return response.json()


def add_tags_to_task(task_id: int, tag_ids: List[int]) -> Dict:
    """Add tags to a task"""
    payload = json.dumps({"tag_ids": tag_ids})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/tasks/{task_id}/tags",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to add tags to task")
    return response.json()


def remove_tags_from_task(task_id: int, tag_ids: List[int]) -> Dict:
    """Remove tags from a task"""
    payload = json.dumps({"tag_ids": tag_ids})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/tasks/{task_id}/tags",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to remove tags from task")
    return response.json()


def add_scoring_criteria_to_tasks(
    task_ids: List[int], scoring_criteria: List[Dict]
) -> Dict:
    """Add scoring criteria to a task"""
    payload = json.dumps({"task_ids": task_ids, "scoring_criteria": scoring_criteria})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/tasks/scoring_criteria",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to add scoring criteria to tasks")
    return response.json()


def remove_scoring_criteria(scoring_criteria_ids: List[int]) -> Dict:
    """Remove scoring criteria from a task"""
    payload = json.dumps({"ids": scoring_criteria_ids})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/tasks/scoring_criteria",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to remove scoring criteria from task")
    return response.json()


def get_courses_for_tasks(task_ids: List[int]) -> List[Dict]:
    """Get courses for multiple tasks"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tasks/courses",
        params={"task_ids": task_ids},
    )

    if response.status_code != 200:
        raise Exception("Failed to get courses for tasks")

    return response.json()


def update_tests_for_task(task_id: int, tests: List[dict]) -> Dict:
    """Update tests for a task"""
    payload = json.dumps({"tests": tests})
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/tasks/{task_id}/tests",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to update tests for task")
    return response.json()
