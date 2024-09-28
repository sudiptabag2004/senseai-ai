import os
from os.path import exists, dirname
from typing import List
from fastapi import FastAPI

from models import ChatMessage, Task, Streaks
from lib.db import get_all_chat_history, get_all_tasks, get_streaks

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
async def get_tasks() -> List[Task]:
    return get_all_tasks()


@app.get(
    "/streaks",
    response_model=Streaks,
)
async def get_all_streaks() -> Streaks:
    return get_streaks()
