from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from api.db import (
    get_all_tasks_for_org_or_course as get_all_tasks_for_org_or_course_from_db,
    get_solved_tasks_for_user as get_solved_tasks_for_user_from_db,
    get_course_task as get_course_task_from_db,
    get_scoring_criteria_for_task as get_scoring_criteria_for_task_from_db,
    store_task as store_task_in_db,
    update_task as update_task_in_db,
    delete_task as delete_task_in_db,
    delete_tasks as delete_tasks_in_db,
    get_all_verified_tasks_for_course as get_all_verified_tasks_for_course_from_db,
    get_scoring_criteria_for_tasks as get_scoring_criteria_for_tasks_from_db,
    add_tags_to_task as add_tags_to_task_in_db,
    remove_tags_from_task as remove_tags_from_task_in_db,
    add_scoring_criteria_to_tasks as add_scoring_criteria_to_tasks_in_db,
    remove_scoring_criteria_from_task as remove_scoring_criteria_from_task_in_db,
    get_courses_for_tasks as get_courses_for_tasks_from_db,
    update_tests_for_task as update_tests_for_task_in_db,
)
from api.models import (
    Task,
    LeaderboardViewType,
    StoreTaskRequest,
    UpdateTaskRequest,
    TaskTagsRequest,
    AddScoringCriteriaToTasksRequest,
    UpdateTaskTestsRequest,
    TaskCourseResponse,
)

router = APIRouter()


@router.get("/", response_model=List[Task])
async def get_tasks_for_org(org_id: int, return_tests: bool = False) -> List[Task]:
    return await get_all_tasks_for_org_or_course_from_db(
        org_id=org_id, return_tests=return_tests
    )


@router.get("/course/{course_id}/verified")
async def get_tasks_for_course(course_id: int, milestone_id: int = None) -> List[Task]:
    return await get_all_verified_tasks_for_course_from_db(course_id, milestone_id)


@router.post("/", response_model=int)
async def store_task(request: StoreTaskRequest) -> int:
    return await store_task_in_db(
        name=request.name,
        description=request.description,
        answer=request.answer,
        tags=request.tags,
        input_type=request.input_type,
        response_type=request.response_type,
        coding_languages=request.coding_languages,
        generation_model=request.generation_model,
        verified=request.verified,
        tests=request.tests,
        org_id=request.org_id,
        context=request.context,
        task_type=request.task_type,
        max_attempts=request.max_attempts,
        is_feedback_shown=request.is_feedback_shown,
    )


@router.get("/courses")
async def get_courses_for_tasks(
    task_ids: List[int] = Query(...),
) -> List[TaskCourseResponse]:
    return await get_courses_for_tasks_from_db(task_ids)


@router.get("/scoring_criteria")
async def get_scoring_criteria_for_tasks(task_ids: List[int] = Query(...)):
    return await get_scoring_criteria_for_tasks_from_db(task_ids)


@router.delete("/scoring_criteria")
async def remove_scoring_criteria_from_task(ids: List[int] = Query(...)):
    await remove_scoring_criteria_from_task_in_db(ids)
    return {"success": True}


@router.post("/scoring_criteria")
async def add_scoring_criteria_to_tasks(request: AddScoringCriteriaToTasksRequest):
    await add_scoring_criteria_to_tasks_in_db(
        request.task_ids, request.scoring_criteria
    )
    return {"success": True}


@router.put("/{task_id}")
async def update_task(task_id: int, request: UpdateTaskRequest):
    await update_task_in_db(
        task_id=task_id,
        name=request.name,
        description=request.description,
        answer=request.answer,
        input_type=request.input_type,
        response_type=request.response_type,
        coding_languages=request.coding_languages,
        context=request.context,
        max_attempts=request.max_attempts,
        is_feedback_shown=request.is_feedback_shown,
    )
    return {"success": True}


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    await delete_task_in_db(task_id)
    return {"success": True}


@router.delete("/")
async def delete_tasks(task_ids: List[int] = Query(...)):
    await delete_tasks_in_db(task_ids)
    return {"success": True}


@router.get("/cohort/{cohort_id}/user/{user_id}/completed", response_model=List[int])
async def get_tasks_completed_for_user(
    user_id: int,
    cohort_id: int,
    view: LeaderboardViewType = str(LeaderboardViewType.ALL_TIME),
) -> List[int]:
    return await get_solved_tasks_for_user_from_db(user_id, cohort_id, view)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: int, course_id: int) -> Task:
    task = await get_course_task_from_db(task_id, course_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/scoring_criteria")
async def get_task_scoring_criteria(task_id: int):
    return await get_scoring_criteria_for_task_from_db(task_id)


@router.post("/{task_id}/tags")
async def add_tags_to_task(task_id: int, request: TaskTagsRequest):
    await add_tags_to_task_in_db(task_id, request.tag_ids)
    return {"success": True}


@router.delete("/{task_id}/tags")
async def remove_tags_from_task(task_id: int, request: TaskTagsRequest):
    await remove_tags_from_task_in_db(task_id, request.tag_ids)
    return {"success": True}


@router.put("/{task_id}/tests")
async def update_task_tests(task_id: int, request: UpdateTaskTestsRequest):
    await update_tests_for_task_in_db(task_id, request.tests)
    return {"success": True}
