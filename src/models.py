from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    id: int
    user_id: str
    task_id: int
    task_name: str
    role: ChatRole
    content: str
    is_solved: bool
    timestamp: str


class Task(BaseModel):
    id: int
    name: str
    description: str
    answer: str
    tags: List[str]
    generation_model: str
    verified: bool
    timestamp: str


Streaks = Dict[str, int]
