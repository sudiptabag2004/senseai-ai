import requests
import os
import json
from typing import Dict, List


def get_tags_for_org(org_id: int) -> List[Dict]:
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/tags/", params={"org_id": org_id}
    )

    if response.status_code != 200:
        raise Exception("Failed to get tags for org")

    return response.json()


def delete_tag_by_id(tag_id: int):
    response = requests.delete(f"{os.getenv('BACKEND_URL')}/tags/{tag_id}")
    if response.status_code != 200:
        raise Exception("Failed to delete tag")

    return response.json()


def create_tag(tag: Dict):
    payload = json.dumps(tag)
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/tags/",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to create tag")

    return response.json()


def create_bulk_tags(tag_names: List[str], org_id: int):
    payload = json.dumps({"tag_names": tag_names, "org_id": org_id})
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/tags/bulk",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to create bulk tags")

    return response.json()
