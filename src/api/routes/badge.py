from fastapi import APIRouter, HTTPException
from typing import List, Dict
from api.db import (
    create_badge_for_user as create_badge_for_user_in_db,
    update_badge as update_badge_in_db,
    get_badge_by_id as get_badge_by_id_from_db,
    get_cohort_badge_by_type_and_user_id as get_cohort_badge_by_type_and_user_id_from_db,
    delete_badge_by_id as delete_badge_by_id_from_db,
    get_badges_by_user_id as get_badges_by_user_id_from_db,
)
from api.models import CreateBadgeRequest, UpdateBadgeRequest

router = APIRouter()


@router.post("/")
async def create_badge_for_user(request: CreateBadgeRequest) -> int:
    return await create_badge_for_user_in_db(
        request.user_id,
        request.value,
        request.badge_type,
        request.image_path,
        request.bg_color,
        request.cohort_id,
    )


@router.put("/{badge_id}")
async def update_badge(badge_id: int, request: UpdateBadgeRequest):
    await update_badge_in_db(
        badge_id,
        request.value,
        request.badge_type,
        request.image_path,
        request.bg_color,
    )
    return {"message": "Badge updated"}


@router.get("/{badge_id}")
async def get_badge_by_id(badge_id: int) -> Dict:
    badge = await get_badge_by_id_from_db(badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    return badge


@router.get("/cohort/{cohort_id}/{user_id}/{badge_type}")
async def get_cohort_badge_by_type_and_user_id(
    cohort_id: int, badge_type: str, user_id: int
) -> Dict:
    badge = await get_cohort_badge_by_type_and_user_id_from_db(
        user_id, badge_type, cohort_id
    )

    if not badge:
        return {}

    return badge


@router.delete("/{badge_id}")
async def delete_badge_by_id(badge_id: int):
    await delete_badge_by_id_from_db(badge_id)
    return {"message": "Badge deleted"}


@router.get("/user/{user_id}")
async def get_badges_by_user_id(user_id: int) -> List[Dict]:
    return await get_badges_by_user_id_from_db(user_id)
