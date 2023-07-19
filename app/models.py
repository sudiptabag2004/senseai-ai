from typing import List, Union, Optional
from typing_extensions import TypedDict
from enum import Enum
from pydantic import BaseModel


class GenerateTrainingQuestionRequest(BaseModel):
    topic: str
    sub_topic: str
    concept: str
    blooms_level: str
    learning_outcome: str


class OpenAIChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TrainingChatUserResponseType(str, Enum):
    ANSWER = "answer"  # irrelevant response by user
    CLARIFICATION = "clarification"  # clarification requested by user
    IRRELEVANT = "irrelevant"  # answer given by user to the question asked


class ChatMessageType(str, Enum):
    QUESTION = "question"  # ai-generated question
    RESPONSE = "response"  # ai-response
    ANSWER = "answer"  # irrelevant response by user
    CLARIFICATION = "clarification"  # clarification requested by user
    IRRELEVANT = "irrelevant"  # answer given by user to the question asked


class ChatMarkupLanguage(BaseModel):
    role: OpenAIChatRole
    content: str
    type: Optional[
        ChatMessageType
    ] = None  # optional as there will be no "type" for the latest user response


class TrainingChatRequest(BaseModel):
    messages: List[ChatMarkupLanguage]


class TrainingEvaluatorResponse(BaseModel):
    answer: int
    feedback: str


class TrainingChatResponse(BaseModel):
    type: TrainingChatUserResponseType
    response: Optional[Union[str, TrainingEvaluatorResponse]]
