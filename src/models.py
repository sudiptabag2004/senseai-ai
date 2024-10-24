from enum import Enum
from pydantic import BaseModel
from typing import List, Dict, Optional


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ResponseType(str, Enum):
    TEXT = "text"
    CODE = "code"


class ChatMessage(BaseModel):
    id: int
    user_id: str
    task_id: int
    task_name: str
    role: ChatRole
    content: str
    is_solved: bool
    response_type: Optional[ResponseType]
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
    milestone_id: Optional[int]
    milestone_name: Optional[str]


Streaks = Dict[str, int]
