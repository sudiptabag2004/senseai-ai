import json
import os
from typing import Dict, List
import requests
import streamlit as st
from lib.utils import generate_random_color
from lib.toast import set_toast


def create_org(org_name: str, logo_color: str, user_id: int):
    payload = json.dumps({"name": org_name, "color": logo_color, "user_id": user_id})
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/organizations",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to create organization")

    return response.json()


@st.dialog("Create an organization")
def show_create_org_dialog(user_id: int):
    with st.form("create_org", border=False):
        cols = st.columns([5, 1])
        with cols[0]:
            org_name = st.text_input(
                "Organization Name*",
                key="org_name",
            )

        color = generate_random_color()

        with cols[1]:
            logo_color = st.color_picker(
                "Logo Color",
                value=color,
                key="logo_color",
            )

        submit_button = st.form_submit_button(
            "Create",
            use_container_width=True,
            type="primary",
        )
        if submit_button:
            response = create_org(org_name, logo_color, user_id)
            st.session_state.user_orgs = response["user_orgs"]

            # updated currently selected org
            st.query_params["org_id"] = st.session_state.user_orgs[0]["id"]

            set_toast("Organization created successfully", "✅")
            st.rerun()


def get_org_by_id(org_id: int) -> Dict:
    response = requests.get(f"{os.getenv('BACKEND_URL')}/organizations/{org_id}")

    if response.status_code != 200:
        raise Exception("Failed to get organization")

    return response.json()


def get_org_members(org_id: int) -> List[Dict]:
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/organizations/{org_id}/members"
    )

    if response.status_code != 200:
        raise Exception("Failed to get organization members")

    return response.json()


def remove_members_from_org(org_id: int, user_ids: List[int]):
    payload = json.dumps({"user_ids": user_ids})
    headers = {"Content-Type": "application/json"}

    response = requests.delete(
        f"{os.getenv('BACKEND_URL')}/organizations/{org_id}/members",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to remove members from organization")

    return response.json()


def add_member_to_org(org_id: int, email: str, role: str):
    payload = json.dumps({"email": email, "role": role})
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/organizations/{org_id}/members",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to add member to organization")

    return response.json()


def update_org_by_id(org_id: int, org: Dict):
    payload = json.dumps(org)
    headers = {"Content-Type": "application/json"}

    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/organizations/{org_id}",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to update organization")

    return response.json()


def update_org_openai_api_key(
    org_id: int, encrypted_openai_api_key: str, is_free_trial: bool
):
    payload = json.dumps(
        {
            "encrypted_openai_api_key": encrypted_openai_api_key,
            "is_free_trial": is_free_trial,
        }
    )
    headers = {"Content-Type": "application/json"}

    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/organizations/{org_id}/openai_api_key",
        headers=headers,
        data=payload,
    )

    if response.status_code != 200:
        raise Exception("Failed to update organization openai api key")

    return response.json()
