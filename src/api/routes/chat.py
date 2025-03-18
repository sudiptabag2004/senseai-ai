from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from api.db import (
    store_messages as store_messages_in_db,
    get_all_chat_history as get_all_chat_history_from_db,
    get_user_chat_history_for_tasks as get_user_chat_history_for_tasks_from_db,
    delete_all_chat_history as delete_all_chat_history_from_db,
)
from api.models import (
    ChatMessage,
    StoreMessagesRequest,
)

router = APIRouter()


@router.post("/", response_model=List[ChatMessage])
async def store_messages(request: StoreMessagesRequest) -> List[ChatMessage]:
    return await store_messages_in_db(
        messages=request.messages,
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
