import requests
import os
import json


def add_cv_review_usage(user_id: int, role: str, ai_review: str):
    payload = json.dumps({"user_id": user_id, "role": role, "ai_review": ai_review})
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/cv_review",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        raise Exception("Failed to add CV review usage")

    return response.json()


def get_all_cv_review_usage():
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/cv_review",
    )

    if response.status_code != 200:
        raise Exception("Failed to get all CV review usage")

    return response.json()
