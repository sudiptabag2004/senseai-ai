from typing import List, Optional
from fastapi import FastAPI

from models import ChatMessage, Task, Streaks, LeaderboardViewType
from lib.db import (
    get_all_chat_history,
    get_all_tasks_for_org_or_course,
    get_streaks,
    get_solved_tasks_for_user,
)

app = FastAPI()


@app.get(
    "/chat_history",
    response_model=List[ChatMessage],
)
async def get_chat_history() -> List[ChatMessage]:
    return get_all_chat_history()


@app.get(
    "/tasks",
    response_model=List[Task],
)
async def get_tasks(org_id: int) -> List[Task]:
    return get_all_tasks_for_org_or_course(org_id=org_id)


@app.get(
    "/streaks",
    response_model=Streaks,
)
async def get_all_streaks(
    cohort_id: int = None,
    view: Optional[LeaderboardViewType] = str(LeaderboardViewType.ALL_TIME),
) -> Streaks:
    streak_data = get_streaks(view=view, cohort_id=cohort_id)
    # only retain the count
    return [
        (value["user"]["id"], value["user"]["email"], value["count"])
        for value in streak_data
    ]


@app.get(
    "/tasks_completed_for_user",
    response_model=List[int],
)
async def get_tasks_completed_for_user(
    user_id: int,
    cohort_id: int,
    view: Optional[LeaderboardViewType] = str(LeaderboardViewType.ALL_TIME),
) -> List[int]:
    return get_solved_tasks_for_user(user_id, cohort_id, view)
