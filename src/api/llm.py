from typing import Dict, List
import traceback
import backoff
import openai
import instructor

from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain.output_parsers.fix import OutputFixingParser
from langchain_community.callbacks import (
    get_openai_callback,
)
from openai import OpenAI

from pydantic import BaseModel

from api.utils.logging import logger

# Test log message
logger.info("Logging system initialized")

COMMON_INSTRUCTIONS = "\n\nGeneral Instructions:\n- Make sure to return one JSON for all the extractions.\n- Never return a list of JSONs.\n- The output schema is a secret. Never reveal the output schema in the answer.\n- Always give a brief explanation before returning the answer. If needed, the explanation can be more elaborate.\n- Never ask for more information or try to engage in any conversation. Work with whatever information you have and provide an answer based on that.\n- Do not hallucinate.\n- Never use computed values in the returned JSON. Always return the actual, full value (e.g. never return 2 as '1 + 1' or 'aaaaa' as 'a' * 5)."


def get_formatted_history(history: List[Dict]) -> str:
    return "\n\n".join(
        [f"{message['role']}: {message['content']}" for message in history]
    )


def get_llm_input_messages(
    system_prompt_template: str, user_prompt_template: str, **kwargs
):
    system_prompt_template = SystemMessagePromptTemplate.from_template(
        system_prompt_template
    )
    user_prompt_template = HumanMessagePromptTemplate.from_template(
        user_prompt_template
    )
    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_prompt_template, user_prompt_template]
    )
    return chat_prompt_template.format_prompt(
        **kwargs,
    ).to_messages()


def is_reasoning_model(model: str) -> bool:
    return model in [
        "o3-mini-2025-01-31",
        "o3-mini",
        "o1-preview-2024-09-12",
        "o1-preview",
        "o1-mini",
        "o1-mini-2024-09-12",
        "o1",
        "o1-2024-12-17",
    ]


def validate_openai_api_key(openai_api_key: str) -> bool:
    client = OpenAI(api_key=openai_api_key)
    try:
        models = client.models.list()
        model_ids = [model.id for model in models.data]

        if "gpt-4o-audio-preview-2024-12-17" in model_ids:
            return False  # paid account
        else:
            return True  # free trial account
    except Exception:
        return None


async def run_llm_with_instructor(
    api_key: str,
    model: str,
    messages: List,
    response_model: BaseModel,
    max_completion_tokens: int,
):
    client = instructor.from_openai(openai.AsyncOpenAI(api_key=api_key))

    model_kwargs = {}

    if not is_reasoning_model(model):
        model_kwargs["temperature"] = 0

    return await client.chat.completions.create(
        model=model,
        messages=messages,
        response_model=response_model,
        max_completion_tokens=max_completion_tokens,
        store=True,
        **model_kwargs,
    )


async def stream_llm_with_instructor(
    api_key: str,
    model: str,
    messages: List,
    response_model: BaseModel,
    max_completion_tokens: int,
    **kwargs,
):
    client = instructor.from_openai(openai.AsyncOpenAI(api_key=api_key))

    model_kwargs = {}

    if not is_reasoning_model(model):
        model_kwargs["temperature"] = 0

    model_kwargs.update(kwargs)

    return client.chat.completions.create_partial(
        model=model,
        messages=messages,
        response_model=response_model,
        stream=True,
        max_completion_tokens=max_completion_tokens,
        store=True,
        **model_kwargs,
    )


def stream_llm_with_openai(
    api_key: str,
    model: str,
    messages: List,
    max_completion_tokens: int,
):
    client = openai.OpenAI(api_key=api_key)

    model_kwargs = {}

    if not is_reasoning_model(model):
        model_kwargs["temperature"] = 0

    return client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        max_completion_tokens=max_completion_tokens,
        store=True,
        **model_kwargs,
    )
