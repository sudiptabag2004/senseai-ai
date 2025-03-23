from fastapi import APIRouter
from typing import List
from api.db import get_all_scorecards_for_org as get_all_scorecards_for_org_from_db
from api.models import Scorecard

router = APIRouter()


@router.get("/", response_model=List[Scorecard])
async def get_all_scorecards_for_org(org_id: int) -> List[Scorecard]:
    return await get_all_scorecards_for_org_from_db(org_id)
