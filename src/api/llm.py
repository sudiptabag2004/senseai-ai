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
from langchain_openai import ChatOpenAI
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


def remove_comments(json_str):
    """Remove comments from the JSON output of the LLM. This is necessary because the LLM output may contain comments which can mess up the output parser"""
    lines = json_str.split("\n")
    cleaned_lines = []

    for line in lines:
        # Remove everything after the first occurrence of '//'
        line = line.split("//")[0]
        cleaned_lines.append(line)

    cleaned_json = "\n".join(cleaned_lines)
    return cleaned_json


def remove_output_schema_from_response(response: str):
    """If there are multiple ``` in the response, only keep the response starting from the second last backtick. This is necessary because the LLM output may contain the output schema which can mess up the output parser."""
    import re

    backtick_instances = [m.start() for m in re.finditer("```", response)]

    # only keep the response starting from the second last backtick
    # ```json.....```
    second_last_backtick_start_index = backtick_instances[-2]
    return response[second_last_backtick_start_index:]


def remove_ending_commas_in_list(response: str) -> str:
    """Remove ending commas in lists to ensure valid JSON while preserving spaces."""
    import re

    # pattern to match a comma followed by optional newline characters and spaces, and a closing bracket (] or })
    pattern = r",(\s*[\]}])"

    # Remove the comma if a match is found to ensure valid JSON
    cleaned_response = re.sub(pattern, r"\1", response)

    return cleaned_response


def remove_string_mistakes(response):
    return response.replace("\\n", "\n")


def clean_llm_output(response: str):
    return remove_ending_commas_in_list(
        remove_comments(
            remove_output_schema_from_response(remove_string_mistakes(response))
        )
    )


def parse_llm_output(
    output_parser,
    response: str,
    model: str,
    api_key: str,
    default={},
    verbose: bool = False,
):
    try:
        return output_parser.parse(response)
    except:
        try:
            return output_parser.parse(clean_llm_output(response))
        except:
            if verbose:
                # import ipdb

                # ipdb.set_trace()
                logger.info("OutputParser exception")
                logger.info(response)
                logger.info(traceback.format_exc())

            output_fixing_parser = OutputFixingParser.from_llm(
                parser=output_parser,
                llm=ChatOpenAI(model_name=model, api_key=api_key, temperature=0),
            )
            try:
                return output_fixing_parser.parse(response)
            except:
                logger.info("OutputParser exception")
                logger.info(response)
                logger.info(traceback.format_exc())
                return default


def get_parsed_output_dict(
    output_parser, llm_output, model: str, api_key: str, verbose: bool = False
) -> Dict:
    """Use the output parser to parse the LLM output and return the parsed output as a dictionary"""
    pred = parse_llm_output(
        output_parser, llm_output, model=model, api_key=api_key, verbose=verbose
    )

    if isinstance(pred, BaseModel):
        pred_dict = pred.model_dump()
    else:
        pred_dict = pred

    if isinstance(pred_dict, list):
        # sometimes the LLM outputs a list of JSONs instead of one JSON
        pred_dict = pred_dict[0]

    return pred_dict


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


@backoff.on_exception(backoff.expo, Exception, max_tries=5, factor=2)
async def call_openai_chat_model(
    messages: List,
    model: str,
    api_key: str,
    max_completion_tokens: int,
    verbose: bool = True,
    **kwargs,
):
    openai_model_kwargs = {
        "max_completion_tokens": max_completion_tokens,
    }

    if not is_reasoning_model(model):
        openai_model_kwargs.update(
            {
                "temperature": 0,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
            }
        )

    input_tokens = 0
    output_tokens = 0
    total_cost = 0

    try:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            **openai_model_kwargs,
            model_kwargs={"store": True},
        )

        with get_openai_callback() as llm_callback:
            ai_response = await llm.ainvoke(messages)
            input_tokens = llm_callback.prompt_tokens
            output_tokens = llm_callback.completion_tokens
            total_cost = llm_callback.total_cost

        ai_response = ai_response.content

        if verbose:
            message = f"model: {model} prompt: {messages} response: {ai_response} input tokens: {input_tokens} output tokens: {output_tokens}"
            logger.info(message)
    except Exception as e:
        traceback.print_exc()
        raise e

    return ai_response


async def call_llm_and_parse_output(
    messages,
    model,
    output_parser,
    api_key: str,
    max_completion_tokens,
    # labels,
    verbose: bool = True,
    **kwargs,
):
    llm_output = await call_openai_chat_model(
        messages,
        model=model,
        api_key=api_key,
        max_completion_tokens=max_completion_tokens,
        # labels=labels,
        verbose=verbose,
        **kwargs,
    )
    return get_parsed_output_dict(
        output_parser,
        llm_output,
        model=model,
        api_key=api_key,
        verbose=verbose,
    )


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
