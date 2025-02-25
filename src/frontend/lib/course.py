import os
import requests
import json
from typing import List, Tuple


def create_course(name: str, org_id: int):
    payload = json.dumps({"name": name, "org_id": org_id})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/courses",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        raise Exception("Failed to create course")

    return response.json()


def add_course_to_cohorts(course_id: int, cohort_ids: List[int]):
    payload = json.dumps({"course_id": course_id, "cohort_ids": cohort_ids})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/courses/{course_id}/cohorts",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        raise Exception("Failed to add course to cohorts")

    return response.json()


def remove_course_from_cohorts(course_id: int, cohort_ids: List[int]):
    payload = json.dumps({"course_id": course_id, "cohort_ids": cohort_ids})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/courses/{course_id}/cohorts",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to remove course from cohorts")

    return response.json()


def get_cohorts_for_course(course_id: int):
    response = requests.get(f"{os.getenv('BACKEND_URL')}/courses/{course_id}/cohorts")

    if response.status_code != 200:
        raise Exception("Failed to get cohorts for course")

    return response.json()


def delete_course(course_id: int):
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/courses/{course_id}")

    if response.status_code != 200:
        raise Exception("Failed to delete course")

    return response.json()


def get_all_courses_for_org(org_id: int):
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/courses", params={"org_id": org_id}
    )

    if response.status_code != 200:
        raise Exception("Failed to get all courses for org")

    return response.json()


def get_tasks_for_course(course_id: int):
    response = requests.get(f"{os.getenv('BACKEND_URL')}/courses/{course_id}/tasks")

    if response.status_code != 200:
        raise Exception("Failed to get tasks for course")

    return response.json()


def update_course_name(course_id: int, name: str):
    payload = json.dumps({"name": name})
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/courses/{course_id}",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to update course name")

    return response.json()


def add_tasks_to_courses(course_tasks: List[Tuple[int, int, int]]):
    payload = json.dumps({"course_tasks": course_tasks})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/courses/tasks",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to add tasks to courses")

    return response.json()


def remove_tasks_from_courses(course_tasks: List[Tuple[int, int]]):
    payload = json.dumps({"course_tasks": course_tasks})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/courses/tasks",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to remove tasks from courses")

    return response.json()


def update_course_task_orders(task_orders: List[Tuple[int, int]]):
    payload = json.dumps({"task_orders": task_orders})
    headers = {"Content-Type": "application/json"}
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/courses/tasks/order",
        data=payload,
        headers=headers,
    )

    if response.status_code != 200:
        raise Exception("Failed to update course task orders")

    return response.json()


def update_course_milestone_order(milestone_orders: List[Tuple[int, int]]):
    payload = json.dumps({"milestone_orders": milestone_orders})
    headers = {"Content-Type": "application/json"}

    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/courses/milestones/order",
        data=payload,
        headers=headers,
    )

    if response.status_code != 200:
        raise Exception("Failed to update course milestone orders")

    return response.json()
