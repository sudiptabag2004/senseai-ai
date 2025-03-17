from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    ai,
)

app = FastAPI()

# Add CORS middleware to allow cross-origin requests (for frontend to access backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(hva.router, prefix="/hva", tags=["hva"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
