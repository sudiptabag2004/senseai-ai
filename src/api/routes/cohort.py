from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from api.db import (
    get_all_cohorts_for_org as get_all_cohorts_for_org_from_db,
    create_cohort as create_cohort_in_db,
    get_cohort_by_id as get_cohort_by_id_from_db,
    add_members_to_cohort as add_members_to_cohort_in_db,
    create_cohort_group as create_cohort_group_in_db,
    delete_cohort_group as delete_cohort_group_from_db,
    remove_members_from_cohort as remove_members_from_cohort_in_db,
    delete_cohort as delete_cohort_from_db,
    update_cohort_name as update_cohort_name_in_db,
    update_cohort_group_name as update_cohort_group_name_in_db,
    add_members_to_cohort_group as add_members_to_cohort_group_in_db,
    remove_members_from_cohort_group as remove_members_from_cohort_group_in_db,
    add_courses_to_cohort as add_courses_to_cohort_in_db,
    remove_courses_from_cohort as remove_courses_from_cohort_in_db,
    get_courses_for_cohort as get_courses_for_cohort_from_db,
    get_mentor_cohort_groups as get_mentor_cohort_groups_from_db,
    get_streaks as get_streaks_from_db,
    get_cohort_group_ids_for_users as get_cohort_group_ids_for_users_from_db,
    get_cohort_analytics_metrics_for_tasks as get_cohort_analytics_metrics_for_tasks_from_db,
    get_cohort_attempt_data_for_tasks as get_cohort_attempt_data_for_tasks_from_db,
)
from api.models import (
    CreateCohortRequest,
    CreateCohortGroupRequest,
    AddMembersToCohortRequest,
    RemoveMembersFromCohortRequest,
    UpdateCohortGroupRequest,
    AddMembersToCohortGroupRequest,
    RemoveMembersFromCohortGroupRequest,
    UpdateCohortRequest,
    UpdateCohortGroupRequest,
    AddCoursesToCohortRequest,
    RemoveCoursesFromCohortRequest,
    Streaks,
    LeaderboardViewType,
)
from api.utils.db import get_new_db_connection

router = APIRouter()


@router.get("/")
async def get_all_cohorts_for_org(org_id: int) -> List[Dict]:
    return await get_all_cohorts_for_org_from_db(org_id)


@router.post("/")
async def create_cohort(request: CreateCohortRequest) -> int:
    return await create_cohort_in_db(request.name, request.org_id)


@router.get("/{cohort_id}")
async def get_cohort_by_id(cohort_id: int) -> Dict:
    cohort_data = await get_cohort_by_id_from_db(cohort_id)
    if not cohort_data:
        raise HTTPException(status_code=404, detail="Cohort not found")

    return cohort_data


@router.post("/{cohort_id}/members")
async def add_members_to_cohort(cohort_id: int, request: AddMembersToCohortRequest):
    try:
        await add_members_to_cohort_in_db(cohort_id, request.emails, request.roles)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{cohort_id}/groups")
async def create_cohort_group(cohort_id: int, request: CreateCohortGroupRequest):
    return await create_cohort_group_in_db(cohort_id, request.name, request.member_ids)


@router.delete("/groups/{group_id}")
async def delete_cohort_group(group_id: int):
    await delete_cohort_group_from_db(group_id)
    return {"success": True}


@router.delete("/{cohort_id}/members")
async def remove_members_from_cohort(
    cohort_id: int, request: RemoveMembersFromCohortRequest
):
    try:
        await remove_members_from_cohort_in_db(cohort_id, request.member_ids)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{cohort_id}")
async def delete_cohort(cohort_id: int):
    await delete_cohort_from_db(cohort_id)
    return {"success": True}


@router.put("/{cohort_id}")
async def update_cohort_name(cohort_id: int, request: UpdateCohortRequest):
    await update_cohort_name_in_db(cohort_id, request.name)
    return {"success": True}


@router.put("/groups/{group_id}")
async def update_cohort_group_name(group_id: int, request: UpdateCohortGroupRequest):
    await update_cohort_group_name_in_db(group_id, request.name)
    return {"success": True}


@router.post("/groups/{group_id}/members")
async def add_members_to_cohort_group(
    group_id: int, request: AddMembersToCohortGroupRequest
):
    try:
        async with get_new_db_connection() as conn:
            cursor = await conn.cursor()
            await add_members_to_cohort_group_in_db(
                cursor, group_id, request.member_ids
            )
            await conn.commit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/groups/{group_id}/members")
async def remove_members_from_cohort_group(
    group_id: int, request: RemoveMembersFromCohortGroupRequest
):
    try:
        await remove_members_from_cohort_group_in_db(group_id, request.member_ids)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{cohort_id}/courses")
async def add_courses_to_cohort(cohort_id: int, request: AddCoursesToCohortRequest):
    await add_courses_to_cohort_in_db(cohort_id, request.course_ids)
    return {"success": True}


@router.delete("/{cohort_id}/courses")
async def remove_courses_from_cohort(
    cohort_id: int, request: RemoveCoursesFromCohortRequest
):
    await remove_courses_from_cohort_in_db(cohort_id, request.course_ids)
    return {"success": True}


@router.get("/{cohort_id}/courses")
async def get_courses_for_cohort(cohort_id: int) -> List[Dict]:
    return await get_courses_for_cohort_from_db(cohort_id)


@router.get("/{cohort_id}/users/{user_id}/groups")
async def get_mentor_cohort_groups(
    cohort_id: int,
    user_id: int,
):
    return await get_mentor_cohort_groups_from_db(user_id, cohort_id)


@router.get("/{cohort_id}/streaks", response_model=Streaks)
async def get_all_streaks_for_cohort(
    cohort_id: int = None, view: LeaderboardViewType = str(LeaderboardViewType.ALL_TIME)
) -> Streaks:
    return await get_streaks_from_db(view=view, cohort_id=cohort_id)


@router.get("/{cohort_id}/groups_for_users")
async def get_cohort_group_ids_for_users(
    cohort_id: int, user_ids: List[int] = Query(...)
):
    return await get_cohort_group_ids_for_users_from_db(cohort_id, user_ids)


@router.get("/{cohort_id}/task_metrics")
async def get_cohort_analytics_metrics_for_tasks(
    cohort_id: int, task_ids: List[int] = Query(...)
):
    return await get_cohort_analytics_metrics_for_tasks_from_db(cohort_id, task_ids)


@router.get("/{cohort_id}/task_attempt_data")
async def get_cohort_attempt_data_for_tasks(
    cohort_id: int, task_ids: List[int] = Query(...)
):
    return await get_cohort_attempt_data_for_tasks_from_db(cohort_id, task_ids)
