from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from pymongo import MongoClient
from bson import ObjectId
import random

from settings import mongodb_uri
from sensai import create_learning_outcomes


class CreateLearningOutcomesRequest(BaseModel):
    subject: str
    topic: str


class AssessmentStartRequest(BaseModel):
    user: str
    subject: str
    topic: str
    bloom_level: str


class AssessmentChatRequest(BaseModel):
    assessment_id: str
    user_message: str


client = MongoClient(mongodb_uri)
db = client["sensai"]
subjects_collection = db["subjects"]
users_collection = db["users"]
assessments_collection = db["assessments"]

app = FastAPI()


@app.get("/")
def read_root():
    print(subjects_collection.find_one({"subject": "JavaScript"}))
    return subjects_collection.find_one({"subject": "JavaScript"})


@app.post("/create_learning_outcomes")
def create_learning_outcomes_endpoint(request: CreateLearningOutcomesRequest):
    subject = request.subject
    topic = request.topic
    learning_outcomes = create_learning_outcomes(subject, topic)
    return learning_outcomes


@app.post("/assessment/start")
def start_assessment(request: AssessmentStartRequest):
    user = request.user
    subject = request.subject
    topic = request.topic
    bloom_level = request.bloom_level

    subject_data = subjects_collection.find_one({"subject": subject})
    if not subject_data:
        return {"error": "subject not found"}

    if topic not in subject_data["roadmap"].keys():
        return {"error": "topic not found"}

    if (
        bloom_level
        not in subject_data["roadmap"][topic]["learning_outcomes"].keys()
    ):
        return {"error": "bloom level not found"}

    learning_outcomes = subject_data["roadmap"][topic]["learning_outcomes"][
        bloom_level
    ]
    learning_outcomes = random.sample(learning_outcomes, 2)

    assessment = {
        "user": user,
        "assessment_cfg": {
            "subject": subject,
            "topic": topic,
            "bloom_level": bloom_level,
        },
        "learning_outcomes": learning_outcomes,
        "assessment_state": {
            "curr_lo_index": 0,
            "finished": False,
            "conversation": [],
            "lo_assessment_state": [
                {
                    "lo": learning_outcomes[idx],
                    "finished": False,
                    "conversation": [],
                }
                for idx in range(len(learning_outcomes))
            ],
        },
    }

    assessments_collection.insert_one(assessment)

    return {"success": True}


@app.post("/assessment/chat")
def assessment_chat(request: AssessmentChatRequest):
    assessment_id = request.assessment_id
    user_message = request.user_message

    assessment = assessments_collection.find_one(
        {"_id": ObjectId(assessment_id)}
    )
    if not assessment:
        return {"error": "assessment not found"}

    return {"success": True}
