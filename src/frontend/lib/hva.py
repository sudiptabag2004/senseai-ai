import requests
import os
import streamlit as st


def is_user_hva_learner(user_id: int) -> bool:
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/hva/is_user_hva_learner",
        params={"user_id": user_id},
    )

    if response.status_code != 200:
        raise Exception("Failed to check if user is HVA learner")

    return response.json()


def get_hva_org_id() -> int:
    if "hva_org_id" in st.session_state:
        return st.session_state.hva_org_id

    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/hva/org_id",
    )

    if response.status_code != 200:
        raise Exception("Failed to get HVA org ID")

    hva_org_id = response.json()

    st.session_state.hva_org_id = hva_org_id
    return hva_org_id


def get_hva_openai_api_key() -> str:
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/hva/openai_key",
    )

    if response.status_code != 200:
        raise Exception("Failed to get HVA openai API key")

    return response.json()
