from enum import Enum
from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Literal
from datetime import datetime


class UserLoginData(BaseModel):
    email: str
    given_name: str
    family_name: str | None = None


class CreateOrganizationRequest(BaseModel):
    name: str
    color: str | None = None
    user_id: int


class CreateOrganizationResponse(BaseModel):
    org_id: int
    user_orgs: List[Dict]


class RemoveMembersFromOrgRequest(BaseModel):
    user_ids: List[int]


class AddUserToOrgRequest(BaseModel):
    email: str
    role: Literal["owner", "admin"]


class UpdateOrgRequest(BaseModel):
    name: str


class UpdateOrgOpenaiApiKeyRequest(BaseModel):
    encrypted_openai_api_key: str
    is_free_trial: bool


class AddMilestoneRequest(BaseModel):
    name: str
    color: str
    org_id: int


class UpdateMilestoneRequest(BaseModel):
    name: str
    color: str


class CreateTagRequest(BaseModel):
    name: str
    org_id: int


class CreateBulkTagsRequest(BaseModel):
    tag_names: List[str]
    org_id: int


class CreateBadgeRequest(BaseModel):
    user_id: int
    value: str
    badge_type: str
    image_path: str
    bg_color: str
    cohort_id: int


class UpdateBadgeRequest(BaseModel):
    value: str
    badge_type: str
    image_path: str
    bg_color: str


class CreateCohortRequest(BaseModel):
    name: str
    org_id: int


class AddMembersToCohortRequest(BaseModel):
    emails: List[str]
    roles: List[str]


class RemoveMembersFromCohortRequest(BaseModel):
    member_ids: List[int]


class UpdateCohortRequest(BaseModel):
    name: str


class UpdateCohortGroupRequest(BaseModel):
    name: str


class CreateCohortGroupRequest(BaseModel):
    name: str
    member_ids: List[int]


class UpdateCohortGroupRequest(BaseModel):
    name: str


class AddMembersToCohortGroupRequest(BaseModel):
    member_ids: List[int]


class RemoveMembersFromCohortGroupRequest(BaseModel):
    member_ids: List[int]


class RemoveCoursesFromCohortRequest(BaseModel):
    course_ids: List[int]


class AddCoursesToCohortRequest(BaseModel):
    course_ids: List[int]


class CreateCourseRequest(BaseModel):
    name: str
    org_id: int


class AddCourseToCohortsRequest(BaseModel):
    cohort_ids: List[int]


class RemoveCourseFromCohortsRequest(BaseModel):
    cohort_ids: List[int]


class UpdateCourseNameRequest(BaseModel):
    name: str


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ResponseType(str, Enum):
    TEXT = "text"
    CODE = "code"
    AUDIO = "audio"


class ChatMessage(BaseModel):
    id: int
    timestamp: str
    user_id: int
    task_id: int
    role: ChatRole | None
    content: Optional[str] | None
    is_solved: bool
    response_type: Optional[ResponseType] | None
    # Optional fields that are only present in some queries
    user_email: Optional[str] = None
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    task_context: Optional[str] = None
    chat_id: Optional[int] = None  # Used in get_user_chat_history_for_tasks


class Tag(BaseModel):
    id: int
    name: str


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


class Task(BaseModel):
    id: int
    name: str
    description: str
    answer: str | None
    tags: List[Tag]
    input_type: TaskInputType | None
    response_type: TaskAIResponseType | None
    coding_language: List[str]
    generation_model: str | None
    verified: bool
    timestamp: str
    org_id: int
    org_name: str
    context: str | None
    type: TaskType
    tests: Optional[List[dict]] = None
    milestone_id: Optional[int] = None
    milestone_name: Optional[str] = None


class User(BaseModel):
    id: int
    email: str
    first_name: str | None
    middle_name: str | None
    last_name: str | None


class UserStreak(BaseModel):
    user: User
    count: int


Streaks = List[UserStreak]


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


class StoreTaskRequest(BaseModel):
    name: str
    description: str
    answer: str | None
    tags: List[Dict]
    input_type: str | None
    response_type: str | None
    coding_languages: List[str] | None
    generation_model: str | None
    verified: bool
    tests: List[dict]
    org_id: int
    context: str | None
    task_type: str


class UpdateTaskRequest(BaseModel):
    name: str
    description: str
    answer: str | None
    input_type: str | None
    response_type: str | None
    coding_languages: List[str] | None
    context: str | None


class StoreMessageRequest(BaseModel):
    user_id: int
    task_id: int
    role: str
    content: str | None
    is_solved: bool = False
    response_type: str | None = None


class GetUserChatHistoryRequest(BaseModel):
    task_ids: List[int]


class TaskTagsRequest(BaseModel):
    tag_ids: List[int]


class AddScoringCriteriaToTasksRequest(BaseModel):
    task_ids: List[int]
    scoring_criteria: List[Dict]


class AddTasksToCoursesRequest(BaseModel):
    course_tasks: List[Tuple[int, int, int | None]]


class RemoveTasksFromCoursesRequest(BaseModel):
    course_tasks: List[Tuple[int, int]]


class UpdateTaskOrdersRequest(BaseModel):
    task_orders: List[Tuple[int, int]]


class UpdateMilestoneOrdersRequest(BaseModel):
    milestone_orders: List[Tuple[int, int]]


class UpdateTaskTestsRequest(BaseModel):
    tests: List[dict]


class Milestone(BaseModel):
    id: int
    name: str | None


class Course(BaseModel):
    id: int
    name: str


class TaskCourse(Course):
    milestone: Milestone | None


class TaskCourseResponse(BaseModel):
    task_id: int
    courses: List[TaskCourse]


class AddCVReviewUsageRequest(BaseModel):
    user_id: int
    role: str
    ai_review: str
