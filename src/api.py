import os
from os.path import exists, dirname
import sys
from typing import List
from fastapi import FastAPI

from models import ChatMessage, Task
from lib.db import get_all_chat_history, get_all_tasks

app = FastAPI()

@app.get(
    "/chat_history",
    response_model=List[ChatMessage],
)
async def get_chat_history(
) -> List[dict]:
    return get_all_chat_history()



@app.get(
    "/tasks",
    response_model=List[Task],
)
async def get_tasks(
) -> List[dict]:
    return get_all_tasks()