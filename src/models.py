from enum import Enum
from pydantic import BaseModel
from typing import List, Tuple, Optional


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ResponseType(str, Enum):
    TEXT = "text"
    CODE = "code"
    AUDIO = "audio"


class ChatMessage(BaseModel):
    id: int
    user_id: int
    user_email: str
    task_id: int
    task_name: str
    role: ChatRole
    content: Optional[str]
    is_solved: bool
    response_type: Optional[ResponseType]
    timestamp: str


class Tag(BaseModel):
    id: int
    name: str


class Task(BaseModel):
    id: int
    name: str
    description: str
    answer: Optional[str]
    tags: List[Tag]
    generation_model: Optional[str]
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


class TaskInputType(Enum):
    CODING = "coding"
    TEXT = "text"
    AUDIO = "audio"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, TaskInputType):
            return self.value == other.value

        raise NotImplementedError()


class TaskAIResponseType(Enum):
    CHAT = "chat"
    REPORT = "report"
    EXAM = "exam"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, TaskAIResponseType):
            return self.value == other.value

        raise NotImplementedError()


class TaskType(Enum):
    QUESTION = "question"
    READING_MATERIAL = "reading_material"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, TaskType):
            return self.value == other.value

        raise NotImplementedError()
