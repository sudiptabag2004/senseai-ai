from fastapi import APIRouter, HTTPException
from typing import List, Dict
from api.db import (
    get_all_milestones_for_org as get_all_milestones_for_org_from_db,
    insert_milestone as insert_milestone_in_db,
    update_milestone as update_milestone_in_db,
    delete_milestone as delete_milestone_from_db,
    get_user_metrics_for_all_milestones as get_user_metrics_for_all_milestones_from_db,
    get_milestones_for_course as get_milestones_for_course_from_db,
)
from api.models import AddMilestoneRequest, UpdateMilestoneRequest

router = APIRouter()


@router.get("/")
async def get_all_milestones_for_org(org_id: int) -> List[Dict]:
    return await get_all_milestones_for_org_from_db(org_id)


@router.post("/")
async def insert_milestone(request: AddMilestoneRequest):
    await insert_milestone_in_db(request.name, request.color, request.org_id)
    return {"message": "Milestone created"}


@router.put("/{milestone_id}")
async def update_milestone(milestone_id: int, request: UpdateMilestoneRequest):
    await update_milestone_in_db(milestone_id, request.name, request.color)
    return {"message": "Milestone updated"}


@router.delete("/{milestone_id}")
async def delete_milestone(milestone_id: int):
    await delete_milestone_from_db(milestone_id)
    return {"message": "Milestone deleted"}


@router.get("/metrics/user/{user_id}/course/{course_id}")
async def get_user_metrics_for_all_milestones(
    user_id: int, course_id: int
) -> List[Dict]:
    return await get_user_metrics_for_all_milestones_from_db(user_id, course_id)


@router.get("/course/{course_id}")
async def get_milestones_for_course(course_id: int) -> List[Dict]:
    return await get_milestones_for_course_from_db(course_id)
