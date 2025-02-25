import os
import json
import requests
from typing import List, Dict
from models import LeaderboardViewType


def get_cohort_by_id(cohort_id: int):
    response = requests.get(f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}")

    if response.status_code != 200:
        raise Exception("Failed to get cohort")

    return response.json()


def add_members_to_cohort(cohort_id: int, emails: List[str], roles: List[str]):
    payload = json.dumps({"emails": emails, "roles": roles})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/members",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to add members to cohort")

    return response.json()


def create_cohort(cohort: Dict):
    payload = json.dumps(cohort)
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/cohorts",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to create cohort")

    return response.json()


def create_cohort_group(name: str, cohort_id: int, member_ids: List[int]):
    payload = json.dumps({"name": name, "member_ids": member_ids})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/groups",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to create cohort group")

    return response.json()


def delete_cohort_group(group_id: int):
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/cohorts/groups/{group_id}")

    if response.status_code != 200:
        raise Exception("Failed to delete cohort group")

    return response.json()


def remove_members_from_cohort(cohort_id: int, member_ids: List[int]):
    payload = json.dumps({"member_ids": member_ids})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/members",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to remove members from cohort")

    return response.json()


def delete_cohort(cohort_id: int):
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}")

    if response.status_code != 200:
        raise Exception("Failed to delete cohort")

    return response.json()


def update_cohort_name(cohort_id: int, name: str):
    payload = json.dumps({"name": name})
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to update cohort name")

    return response.json()


def update_cohort_group_name(group_id: int, name: str):
    payload = json.dumps({"name": name})
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/cohorts/groups/{group_id}",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to update cohort group name")

    return response.json()


def add_members_to_cohort_group(group_id: int, member_ids: List[int]):
    payload = json.dumps({"member_ids": member_ids})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/cohorts/groups/{group_id}/members",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to add members to cohort group")

    return response.json()


def remove_members_from_cohort_group(group_id: int, member_ids: List[int]):
    payload = json.dumps({"member_ids": member_ids})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/cohorts/groups/{group_id}/members",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to remove members from cohort group")

    return response.json()


def add_courses_to_cohort(cohort_id: int, course_ids: List[int]):
    payload = json.dumps({"course_ids": course_ids})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/courses",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to add courses to cohort")

    return response.json()


def remove_courses_from_cohort(cohort_id: int, course_ids: List[int]):
    payload = json.dumps({"course_ids": course_ids})
    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/courses",
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to remove courses from cohort")

    return response.json()


def get_courses_for_cohort(cohort_id: int):
    response = requests.get(f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/courses")

    if response.status_code != 200:
        raise Exception("Failed to get courses for cohort")

    return response.json()


def get_cohorts_for_org(org_id: int):
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cohorts", params={"org_id": org_id}
    )

    if response.status_code != 200:
        raise Exception("Failed to get cohorts for org")

    return response.json()


def get_mentor_cohort_groups(cohort_id: int, user_id: int):
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/users/{user_id}/groups"
    )

    if response.status_code != 200:
        raise Exception("Failed to get mentor cohort groups")

    return response.json()


def get_all_streaks_for_cohort(
    cohort_id: int, view: str = str(LeaderboardViewType.ALL_TIME)
):
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/streaks",
        params={"view": view},
    )

    if response.status_code != 200:
        raise Exception("Failed to get all streaks for cohort")

    return response.json()


def get_cohort_group_ids_for_users(cohort_id: int, user_ids: List[int]):
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/groups_for_users",
        params={"user_ids": user_ids},
    )

    if response.status_code != 200:
        raise Exception("Failed to get cohort group ids for users")

    return response.json()


def get_cohort_analytics_metrics_for_tasks(cohort_id: int, task_ids: List[int]) -> Dict:
    """Get analytics metrics for a cohort"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/task_metrics",
        params={"task_ids": task_ids},
    )

    if response.status_code != 200:
        raise Exception("Failed to get cohort analytics metrics for tasks")

    return response.json()


def get_cohort_attempt_data_for_tasks(cohort_id: int, task_ids: List[int]) -> Dict:
    """Get attempt data for a cohort"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cohorts/{cohort_id}/task_attempt_data",
        params={"task_ids": task_ids},
    )

    if response.status_code != 200:
        raise Exception("Failed to get cohort attempt data for tasks")

    return response.json()
