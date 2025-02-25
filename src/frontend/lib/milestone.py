import os
from typing import Dict, List
import requests
import json


def get_milestones_for_org(org_id: int) -> List[Dict]:
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/milestones/", params={"org_id": org_id}
    )

    if response.status_code != 200:
        raise Exception("Failed to get milestones")

    return response.json()


def get_milestones_for_course(course_id: int) -> List[Dict]:
    response = requests.get(f"{os.getenv('BACKEND_URL')}/milestones/course/{course_id}")

    if response.status_code != 200:
        raise Exception("Failed to get milestones")

    return response.json()


def delete_milestone_by_id(milestone_id: int):
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/milestones/{milestone_id}")
    if response.status_code != 200:
        raise Exception("Failed to delete milestone")

    return response.json()


def update_milestone_by_id(milestone_id: int, milestone: Dict):
    payload = json.dumps(milestone)
    headers = {"Content-Type": "application/json"}

    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/milestones/{milestone_id}",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to update milestone")

    return response.json()


def create_milestone(milestone: Dict):
    payload = json.dumps(milestone)
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/milestones/",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to create milestone")

    return response.json()


def get_user_metrics_for_all_milestones(user_id: int, course_id: int):
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/milestones/metrics/user/{user_id}/course/{course_id}"
    )
    if response.status_code != 200:
        raise Exception("Failed to get user metrics for all milestones")

    return response.json()
