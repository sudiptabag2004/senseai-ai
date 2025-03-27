from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from api.db import (
    get_solved_tasks_for_user as get_solved_tasks_for_user_from_db,
    get_task as get_task_from_db,
    get_scoring_criteria_for_task as get_scoring_criteria_for_task_from_db,
    delete_task as delete_task_in_db,
    delete_tasks as delete_tasks_in_db,
    get_scoring_criteria_for_tasks as get_scoring_criteria_for_tasks_from_db,
    add_tags_to_task as add_tags_to_task_in_db,
    remove_tags_from_task as remove_tags_from_task_in_db,
    add_scoring_criteria_to_tasks as add_scoring_criteria_to_tasks_in_db,
    remove_scoring_criteria_from_task as remove_scoring_criteria_from_task_in_db,
    get_courses_for_tasks as get_courses_for_tasks_from_db,
    update_tests_for_task as update_tests_for_task_in_db,
    create_draft_task_for_course as create_draft_task_for_course_in_db,
    publish_learning_material_task as publish_learning_material_task_in_db,
    publish_quiz as publish_quiz_in_db,
    update_quiz as update_quiz_in_db,
    mark_task_completed as mark_task_completed_in_db,
    get_all_learning_material_tasks_for_course as get_all_learning_material_tasks_for_course_from_db,
)
from api.models import (
    Task,
    LearningMaterialTask,
    QuizTask,
    LeaderboardViewType,
    PublishQuizRequest,
    UpdateTaskRequest,
    TaskTagsRequest,
    AddScoringCriteriaToTasksRequest,
    UpdateTaskTestsRequest,
    CreateDraftTaskRequest,
    TaskCourseResponse,
    CreateDraftTaskResponse,
    PublishLearningMaterialTaskRequest,
    UpdateQuestionRequest,
    UpdateQuizRequest,
    MarkTaskCompletedRequest,
)

router = APIRouter()


@router.get("/course/{course_id}/learning_material")
async def get_learning_material_tasks_for_course(
    course_id: int,
) -> List[Task]:
    return await get_all_learning_material_tasks_for_course_from_db(course_id)


@router.post("/", response_model=CreateDraftTaskResponse)
async def create_draft_task_for_course(
    request: CreateDraftTaskRequest,
) -> CreateDraftTaskResponse:
    id = await create_draft_task_for_course_in_db(
        request.title,
        str(request.type),
        request.org_id,
        request.course_id,
        request.milestone_id,
    )
    return {"id": id}


@router.post("/{task_id}/learning_material", response_model=LearningMaterialTask)
async def publish_learning_material_task(
    task_id: int, request: PublishLearningMaterialTaskRequest
) -> LearningMaterialTask:
    result = await publish_learning_material_task_in_db(
        task_id, request.title, request.blocks
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.post("/{task_id}/quiz", response_model=QuizTask)
async def publish_quiz(task_id: int, request: PublishQuizRequest) -> QuizTask:
    result = await publish_quiz_in_db(
        task_id=task_id,
        title=request.title,
        questions=request.questions,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.put("/{task_id}/quiz", response_model=QuizTask)
async def update_quiz(task_id: int, request: UpdateQuizRequest) -> QuizTask:
    result = await update_quiz_in_db(
        task_id=task_id,
        title=request.title,
        questions=request.questions,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


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


@router.get("/{task_id}")
async def get_task(task_id: int) -> LearningMaterialTask | QuizTask:
    task = await get_task_from_db(task_id)
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


@router.post("/{task_id}/complete")
async def mark_task_completed(task_id: int, request: MarkTaskCompletedRequest):
    await mark_task_completed_in_db(task_id, request.user_id)
    return {"success": True}
