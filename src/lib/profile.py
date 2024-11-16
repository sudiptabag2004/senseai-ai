from typing import Literal, Dict


def get_user_name(user: Dict, name_type: Literal["full", "first"] = "full"):
    if user is None:
        return None

    if not user["first_name"]:
        return ""

    if name_type == "first":
        return user["first_name"].strip()

    middle_name = ""
    if user["middle_name"]:
        middle_name = f" {user['middle_name']}"

    full_name = f"{user['first_name']}{middle_name} {user['last_name']}"
    return full_name.strip()
