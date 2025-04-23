from typing import Annotated, Dict, List, Optional, Tuple
from fastapi import FastAPI, Body
from api.models import (
    PublicAPIChatMessage,
    CourseWithMilestonesAndTaskDetails,
    TaskType,
)
from api.db import (
    get_all_chat_history as get_all_chat_history_from_db,
    get_course as get_course_from_db,
    get_task as get_task_from_db,
)

app = FastAPI()


@app.get(
    "/chat_history",
    response_model=List[PublicAPIChatMessage],
)
async def get_all_chat_history(org_id: int) -> List[PublicAPIChatMessage]:
    return await get_all_chat_history_from_db(org_id)


@app.get(
    "/course/{course_id}",
    response_model=CourseWithMilestonesAndTaskDetails,
)
async def get_tasks_for_course(course_id: int) -> CourseWithMilestonesAndTaskDetails:
    course = await get_course_from_db(course_id=course_id)

    for milestone in course["milestones"]:
        for task in milestone["tasks"]:
            if task["type"] != TaskType.LEARNING_MATERIAL:
                continue

            task_details = await get_task_from_db(task["id"])
            task["blocks"] = task_details["blocks"]

    return course


# @app.get(
#     "/streaks",
# )
# async def get_all_streaks(
#     cohort_id: int = None,
#     view: Optional[LeaderboardViewType] = str(LeaderboardViewType.ALL_TIME),
# ) -> List[Tuple]:
#     streak_data = await get_cohort_streaks_from_db(view=view, cohort_id=cohort_id)
#     # only retain the count
#     return [
#         (value["user"]["id"], value["user"]["email"], value["count"])
#         for value in streak_data
#     ]


# @app.get(
#     "/tasks_completed_for_user",
#     response_model=List[int],
# )
# async def get_tasks_completed_for_user(
#     user_id: int,
#     cohort_id: int,
#     view: Optional[LeaderboardViewType] = str(LeaderboardViewType.ALL_TIME),
# ) -> List[int]:
#     return await get_solved_tasks_for_user_from_db(user_id, cohort_id, view)


# @app.post(
#     "/cohorts/{cohort_id}/add_learners",
# )
# async def add_learners_to_cohort(
#     cohort_id: int,
#     emails: Annotated[List[str], Body(embed=True)],
# ) -> Dict:
#     roles = ["learner" for _ in range(len(emails))]
#     await add_members_to_cohort_in_db(cohort_id, emails, roles)
#     return {"message": "Learners added to cohort"}
