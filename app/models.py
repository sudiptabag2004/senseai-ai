from typing import List, Union, Optional
from typing_extensions import TypedDict
from enum import Enum
from pydantic import BaseModel, Field


class OpenAIChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageType(str, Enum):
    QUESTION = "question"  # ai-generated question
    RESPONSE = "response"  # ai-response
    SOLUTION = "solution"  # ai-solution
    INTEREST = "interest"  # ai-question for eliciting user interest
    INTEREST_RESPONSE = "interest_response"  # user response to interest question
    ANSWER = "answer"  # irrelevant response by user
    CLARIFICATION = "clarification"  # clarification requested by user
    IRRELEVANT = "irrelevant"  # answer given by user to the question asked
    MISCELLANEOUS = "miscellaneous"  # user response which is neither answer nor clarification (e.g. acknowledge - "okay", "no")


class ChatMarkupLanguage(BaseModel):
    role: OpenAIChatRole
    content: str
    type: Optional[
        ChatMessageType
    ] = None  # optional as there will be no "type" for the latest user response


class GenerateTrainingQuestionRequest(BaseModel):
    topic: str
    sub_topic: str
    concept: str
    blooms_level: str
    learning_outcome: str


class EnglishDifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EnglishActivityType(str, Enum):
    READING = "reading"
    LISTENING = "listening"


class GenerateEnglishRequestBase(BaseModel):
    theme: str
    difficulty_level: EnglishDifficultyLevel
    grade_level: str


class GenerateEnglishPassageRequest(GenerateEnglishRequestBase):
    learning_outcomes: list[str]
    activity_type: EnglishActivityType
    messages: List[ChatMarkupLanguage]
    temperature: Optional[float]


class GenerateEnglishQuestionRequest(GenerateEnglishRequestBase):
    learning_outcome: str
    passage: str


class EnglishFeedbackLanguage(str, Enum):
    ENGLISH = "English"
    TAMIL = "Tamil"
    HINDI = "Hindi"
    KANNADA = "Kannada"
    TELUGU = "Telugu"


class EnglishEvaluationRequest(BaseModel):
    difficulty_level: EnglishDifficultyLevel
    messages: List[ChatMarkupLanguage]


class TTSVoice(str, Enum):
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


class TTSModel(str, Enum):
    TTS1 = "tts-1"
    TTS1HD = "tts-1-hd"


class TTSRequestParams(BaseModel):
    voice: Optional[TTSVoice] = Field(default=TTSVoice.ECHO)
    text: str
    model: Optional[TTSModel] = Field(default=TTSModel.TTS1)


class TrainingChatUserResponseType(str, Enum):
    ANSWER = "answer"  # irrelevant response by user
    CLARIFICATION = "clarification"  # clarification requested by user
    IRRELEVANT = "irrelevant"  # answer given by user to the question asked
    MISCELLANEOUS = "miscellaneous"  # user response which is neither answer nor clarification (e.g. acknowledge - "okay", "no")


class TrainingChatRequest(BaseModel):
    messages: List[ChatMarkupLanguage]
    general_setup: Optional[str] = None
    evaluator_setup: Optional[str] = None
    is_solution_provided: Optional[bool] = False


class TrainingEvaluatorResponse(BaseModel):
    answer: int
    feedback: str


class TrainingChatResponse(BaseModel):
    type: TrainingChatUserResponseType
    response: Optional[Union[str, TrainingEvaluatorResponse]]
