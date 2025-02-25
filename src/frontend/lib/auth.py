import os
import json
import requests


def login_or_signup_user(email: str, given_name: str, family_name: str):
    url = f"{os.getenv('BACKEND_URL')}/auth/login"

    payload = json.dumps(
        {
            "email": email,
            "given_name": given_name,
            "family_name": family_name,
        }
    )

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code != 200:
        raise Exception("Failed to login")

    return response.json()
