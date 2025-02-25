from fastapi import APIRouter, Depends
from typing import List, Dict
from api.db import (
    insert_or_return_user,
    get_user_organizations,
)
from api.utils.db import get_new_db_connection
from api.models import UserLoginData

router = APIRouter()


@router.post("/login")
async def login_or_signup_user(user_data: UserLoginData) -> Dict:

    # cursor = await conn.cursor()

    async with get_new_db_connection() as conn:
        cursor = await conn.cursor()
        user = await insert_or_return_user(
            cursor, user_data.email, user_data.given_name, user_data.family_name
        )
        await conn.commit()

    user_orgs = await get_user_organizations(user["id"])

    response = {
        "user": user,
        "user_orgs": user_orgs,
    }

    return response
