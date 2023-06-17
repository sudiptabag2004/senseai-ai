from typing import List, Union, Optional
from typing_extensions import TypedDict
from enum import Enum
from pydantic import BaseModel


class GenerateTrainingQuestionRequest(BaseModel):
    topic: str
    blooms_level: str
    learning_outcome: str


class GenerateTrainingQuestionResponse(BaseModel):
    success: bool
    question: str


class OpenAIChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMarkupLanguage(BaseModel):
    role: OpenAIChatRole
    content: str


class TrainingChatRequest(BaseModel):
    messages: List[ChatMarkupLanguage]


class TrainingEvaluatorResponse(BaseModel):
    answer: int
    feedback: str


class TrainingChatQueryType(str, Enum):
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    IRRELEVANT = "irrelevant"


class TrainingChatResponse(BaseModel):
    type: TrainingChatQueryType
    response: Optional[Union[str, TrainingEvaluatorResponse]]
