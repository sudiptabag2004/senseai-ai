from enum import Enum
from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Literal
from datetime import datetime


class UserLoginData(BaseModel):
    email: str
    given_name: str
    family_name: str | None = None
    id_token: str  # Google authentication token


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: str
    user_id: int


class CreateOrganizationResponse(BaseModel):
    id: int


class RemoveMembersFromOrgRequest(BaseModel):
    user_ids: List[int]


class AddUsersToOrgRequest(BaseModel):
    emails: List[str]


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


class CreateCohortResponse(BaseModel):
    id: int


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


class CreateCourseResponse(BaseModel):
    id: int


class Course(BaseModel):
    id: int
    name: str


class Milestone(BaseModel):
    id: int
    name: str | None
    color: Optional[str] = None
    ordering: Optional[int] = None


class TaskType(Enum):
    EXAM = "exam"
    QUIZ = "quiz"
    LEARNING_MATERIAL = "learning_material"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, TaskType):
            return self.value == other.value

        raise NotImplementedError()


class TaskStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, TaskStatus):
            return self.value == other.value

        raise NotImplementedError()


class Task(BaseModel):
    id: int
    title: str
    type: TaskType
    status: TaskStatus


class Block(BaseModel):
    id: str
    type: str
    props: Dict
    content: List
    children: List
    position: Optional[int] = (
        None  # not present when sent from frontend at the time of publishing
    )


class LearningMaterialTask(Task):
    blocks: List[Block]


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


class QuestionType(Enum):
    OPEN_ENDED = "subjective"
    OBJECTIVE = "objective"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        elif isinstance(other, QuestionType):
            return self.value == other.value


class ScorecardCriterion(BaseModel):
    name: str
    description: str
    min_score: float
    max_score: float


class BaseScorecard(BaseModel):
    title: str
    criteria: List[ScorecardCriterion]


class NewScorecard(BaseScorecard):
    id: str | int


class Scorecard(BaseScorecard):
    id: int


class DraftQuestion(BaseModel):
    blocks: List[Block]
    answer: str | None
    type: QuestionType
    input_type: TaskInputType
    response_type: TaskAIResponseType
    scorecard: Optional[NewScorecard] = None
    context: Dict | None


class PublishedQuestion(DraftQuestion):
    id: int
    scorecard_id: Optional[int] = None


class QuizTask(Task):
    questions: List[PublishedQuestion]


class MilestoneTask(Task):
    ordering: int


class MilestoneWithTasks(Milestone):
    tasks: List[MilestoneTask]


class CourseWithMilestonesAndTasks(Course):
    milestones: List[MilestoneWithTasks]


class UserCourseRole(str, Enum):
    ADMIN = "admin"
    LEARNER = "learner"
    MENTOR = "mentor"


class Organization(BaseModel):
    id: int
    name: str
    slug: str


class UserCourse(Course):
    role: UserCourseRole
    org: Organization


class AddCourseToCohortsRequest(BaseModel):
    cohort_ids: List[int]


class RemoveCourseFromCohortsRequest(BaseModel):
    cohort_ids: List[int]


class UpdateCourseNameRequest(BaseModel):
    name: str


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatResponseType(str, Enum):
    TEXT = "text"
    CODE = "code"
    AUDIO = "audio"


class ChatMessage(BaseModel):
    id: int
    created_at: str
    user_id: int
    question_id: int
    role: ChatRole | None
    content: Optional[str] | None
    response_type: Optional[ChatResponseType] | None


class Tag(BaseModel):
    id: int
    name: str


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


class CreateDraftTaskRequest(BaseModel):
    org_id: int
    course_id: int
    milestone_id: int
    type: TaskType
    title: str


class CreateDraftTaskResponse(BaseModel):
    id: int


class PublishLearningMaterialTaskRequest(BaseModel):
    title: str
    blocks: List[dict]


class PublishQuestionRequest(DraftQuestion):
    coding_languages: List[str] | None
    generation_model: str | None
    max_attempts: int | None
    is_feedback_shown: bool | None
    scorecard_id: Optional[int] = None
    scorecard: Optional[NewScorecard] = None
    context: Dict | None


class PublishQuizRequest(BaseModel):
    title: str
    questions: List[PublishQuestionRequest]


class UpdateQuestionRequest(BaseModel):
    id: int
    blocks: List[dict]
    answer: str | None
    input_type: TaskInputType | None
    context: Dict | None


class UpdateQuizRequest(BaseModel):
    title: str
    questions: List[UpdateQuestionRequest]


class UpdateTaskRequest(BaseModel):
    name: str
    description: str
    answer: str | None
    input_type: str | None
    response_type: str | None
    coding_languages: List[str] | None
    context: str | None
    max_attempts: int | None
    is_feedback_shown: bool | None


class StoreMessageRequest(BaseModel):
    role: str
    content: str | None
    response_type: ChatResponseType | None = None
    created_at: datetime


class StoreMessagesRequest(BaseModel):
    messages: List[StoreMessageRequest]
    user_id: int
    question_id: int
    is_complete: bool


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


class AddMilestoneToCourseRequest(BaseModel):
    name: str
    color: str
    org_id: int


class AddMilestoneToCourseResponse(BaseModel):
    id: int


class UpdateMilestoneOrdersRequest(BaseModel):
    milestone_orders: List[Tuple[int, int]]


class UpdateTaskTestsRequest(BaseModel):
    tests: List[dict]


class TaskCourse(Course):
    milestone: Milestone | None


class TaskCourseResponse(BaseModel):
    task_id: int
    courses: List[TaskCourse]


class AddCVReviewUsageRequest(BaseModel):
    user_id: int
    role: str
    ai_review: str


class UserCohort(BaseModel):
    id: int
    name: str
    role: Literal[UserCourseRole.LEARNER, UserCourseRole.MENTOR]


class AIChatRequest(BaseModel):
    user_response: str
    question: Optional[DraftQuestion] = None
    chat_history: Optional[List[Dict]] = None
    question_id: Optional[int] = None
    user_id: Optional[int] = None
    response_type: Optional[ChatResponseType] = None


class MarkTaskCompletedRequest(BaseModel):
    user_id: int


class GetUserStreakResponse(BaseModel):
    streak_count: int
    active_days: List[str]


class PresignedUrlRequest(BaseModel):
    file_type: str
    content_type: str = "audio/wav"


class PresignedUrlResponse(BaseModel):
    presigned_url: str
    file_key: str
    file_uuid: str


class S3FetchPresignedUrlResponse(BaseModel):
    url: str
