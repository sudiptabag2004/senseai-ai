import os
from os.path import exists, dirname
import sys
from typing import List
from fastapi import FastAPI

from models import ChatMessage
from lib.db import get_all_chat_history

app = FastAPI()

@app.get(
    "/chat_history",
    response_model=List[ChatMessage],
    # dependencies=[Depends(init_wandb_for_generate_question)],
)
async def get_chat_history(
) -> List[dict]:
    return get_all_chat_history()