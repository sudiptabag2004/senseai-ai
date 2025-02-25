from fastapi import APIRouter, HTTPException
from typing import List, Dict
from api.db import (
    get_all_tags_for_org as get_all_tags_for_org_from_db,
    create_tag as create_tag_in_db,
    delete_tag as delete_tag_from_db,
    create_bulk_tags as create_bulk_tags_in_db,
)
from api.models import CreateTagRequest, CreateBulkTagsRequest

router = APIRouter()


@router.get("/")
async def get_all_tags_for_org(org_id: int) -> List[Dict]:
    return await get_all_tags_for_org_from_db(org_id)


@router.post("/")
async def create_tag(request: CreateTagRequest):
    await create_tag_in_db(request.name, request.org_id)
    return {"message": "Tag created"}


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int):
    await delete_tag_from_db(tag_id)
    return {"message": "Tag deleted"}


@router.post("/bulk")
async def create_bulk_tags(request: CreateBulkTagsRequest):
    has_new_tags = await create_bulk_tags_in_db(request.tag_names, request.org_id)
    return {"has_new_tags": has_new_tags}
