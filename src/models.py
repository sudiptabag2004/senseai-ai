from enum import Enum
from pydantic import BaseModel, Field


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
    timestamp: str