from typing import List
from enum import Enum
from pydantic import BaseModel


class GenerateTrainingQuestionRequest(BaseModel):
    topic: str
    blooms_level: str
    learning_outcome: str


class GenerateTrainingQuestionResponse(BaseModel):
    success: bool
    question: str


class OpenAIChatRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class OpenAIChatMessage(BaseModel):
    role: OpenAIChatRole
    content: str


# class GenerateQuestionre
class TrainingChatRequest(BaseModel):
    messages: List[OpenAIChatMessage]
