from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from api.db import (
    store_message as store_message_in_db,
    get_all_chat_history as get_all_chat_history_from_db,
    get_user_chat_history_for_tasks as get_user_chat_history_for_tasks_from_db,
    delete_all_chat_history as delete_all_chat_history_from_db,
)
from api.models import (
    ChatMessage,
    StoreMessageRequest,
)

router = APIRouter()


@router.post("/", response_model=ChatMessage)
async def store_message(request: StoreMessageRequest) -> ChatMessage:
    return await store_message_in_db(
        user_id=request.user_id,
        task_id=request.task_id,
        role=request.role,
        content=request.content,
        is_solved=request.is_solved,
        response_type=request.response_type,
    )


@router.get("/", response_model=List[ChatMessage])
async def get_all_chat_history(org_id: int) -> List[ChatMessage]:
    return await get_all_chat_history_from_db(org_id)


@router.get("/user/{user_id}/tasks", response_model=List[Dict])
async def get_user_chat_history_for_tasks(
    user_id: int, task_ids: List[int] = Query(...)
) -> List[Dict]:
    return await get_user_chat_history_for_tasks_from_db(
        task_ids=task_ids, user_id=user_id
    )


@router.delete("/")
async def delete_all_chat_history():
    await delete_all_chat_history_from_db()
    return {"message": "All chat history deleted"}
