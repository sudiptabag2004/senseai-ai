import os
from typing import Dict, List
import requests
import json


def get_badge_by_id(badge_id: int) -> Dict:
    response = requests.get(f"{os.getenv('BACKEND_URL')}/badges/{badge_id}")
    if response.status_code != 200:
        raise Exception("Failed to get badge")
    return response.json()


def get_cohort_badge_by_type_and_user_id(
    user_id: int, badge_type: str, cohort_id: int
) -> Dict:
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/badges/cohort/{cohort_id}/{user_id}/{badge_type}"
    )
    if response.status_code != 200:
        raise Exception("Failed to get cohort badge")

    return response.json()


def get_all_badges_for_user(user_id: int) -> List[Dict]:
    response = requests.get(f"{os.getenv('BACKEND_URL')}/badges/user/{user_id}")
    if response.status_code != 200:
        raise Exception("Failed to get all badges for user")
    return response.json()


def delete_badge_by_id(badge_id: int):
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/badges/{badge_id}")
    if response.status_code != 200:
        raise Exception("Failed to delete badge")


def create_badge(badge: Dict):
    payload = json.dumps(badge)
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/badges", headers=headers, data=payload
    )

    if response.status_code != 200:
        raise Exception("Failed to create badge")

    return response.json()


def update_badge(
    badge_id: int, value: str, badge_type: str, image_path: str, bg_color: str
):
    payload = json.dumps(
        {
            "value": value,
            "badge_type": badge_type,
            "image_path": image_path,
            "bg_color": bg_color,
        }
    )
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/badges/{badge_id}",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    if response.status_code != 200:
        raise Exception("Failed to update badge")
