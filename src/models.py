from enum import Enum
from pydantic import BaseModel
from typing import List, Tuple, Optional


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ResponseType(str, Enum):
    TEXT = "text"
    CODE = "code"


class ChatMessage(BaseModel):
    id: int
    user_id: int
    user_email: str
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


Streaks = List[Tuple]


class LeaderboardViewType(Enum):
    ALL_TIME = "All time"
    WEEKLY = "This week"
    MONTHLY = "This month"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, LeaderboardViewType):
            return self.value == other.value

        raise NotImplementedError()
