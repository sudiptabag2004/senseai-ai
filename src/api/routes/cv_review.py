from fastapi import APIRouter, HTTPException
from typing import List, Dict
from api.db import (
    add_cv_review_usage as add_cv_review_usage_from_db,
    get_all_cv_review_usage as get_all_cv_review_usage_from_db,
)
from api.models import AddCVReviewUsageRequest

router = APIRouter()


@router.post("/")
async def add_cv_review_usage(request: AddCVReviewUsageRequest):
    await add_cv_review_usage_from_db(request.user_id, request.role, request.ai_review)
    return {"message": "CV review usage added"}


@router.get("/")
async def get_all_cv_review_usage() -> List[Dict]:
    return await get_all_cv_review_usage_from_db()
