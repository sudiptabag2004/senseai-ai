import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from os.path import exists
from api.config import UPLOAD_FOLDER_NAME
from api.routes import (
    auth,
    badge,
    cohort,
    course,
    org,
    tag,
    task,
    chat,
    user,
    cv_review,
    milestone,
    hva,
    file,
    ai,
    scorecard,
)
from api.routes.ai import (
    resume_pending_task_generation_jobs,
    resume_pending_course_structure_generation_jobs,
)
from api.websockets import router as websocket_router
from api.scheduler import scheduler
from api.settings import settings
import sentry_sdk


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()

    # Create the uploads directory if it doesn't exist
    os.makedirs(settings.local_upload_folder, exist_ok=True)

    # Add recovery logic for interrupted tasks
    asyncio.create_task(resume_pending_task_generation_jobs())
    asyncio.create_task(resume_pending_course_structure_generation_jobs())

    yield
    scheduler.shutdown()


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        environment=settings.env,
    )


app = FastAPI(lifespan=lifespan)


# Add CORS middleware to allow cross-origin requests (for frontend to access backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the uploads folder as a static directory
if exists(settings.local_upload_folder):
    app.mount(
        f"/{UPLOAD_FOLDER_NAME}",
        StaticFiles(directory=settings.local_upload_folder),
        name="uploads",
    )

app.include_router(file.router, prefix="/file", tags=["file"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(task.router, prefix="/tasks", tags=["tasks"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(org.router, prefix="/organizations", tags=["organizations"])
app.include_router(cohort.router, prefix="/cohorts", tags=["cohorts"])
app.include_router(course.router, prefix="/courses", tags=["courses"])
app.include_router(badge.router, prefix="/badges", tags=["badges"])
app.include_router(cv_review.router, prefix="/cv_review", tags=["cv_review"])
app.include_router(tag.router, prefix="/tags", tags=["tags"])
app.include_router(milestone.router, prefix="/milestones", tags=["milestones"])
app.include_router(scorecard.router, prefix="/scorecards", tags=["scorecards"])
app.include_router(hva.router, prefix="/hva", tags=["hva"])
app.include_router(websocket_router, prefix="/ws", tags=["websockets"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
