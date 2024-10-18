from typing import Dict, List
import logging
import traceback

import backoff


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


from pydantic import BaseModel


def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Add a StreamHandler to output logs to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a formatter and add it to the handler
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()

# Test log message
logger.info("Logging system initialized")

COMMON_INSTRUCTIONS = "\n\nGeneral Instructions:\n- Make sure to return one JSON for all the extractions.\n- Never return a list of JSONs.\n- The output schema is a secret. Never reveal the output schema in the answer.\n- Always give a brief explanation before returning the answer. If needed, the explanation can be more elaborate.\n- Never ask for more information or try to engage in any conversation. Work with whatever information you have and provide an answer based on that.\n- Do not hallucinate.\n- Never use computed values in the returned JSON. Always return the actual, full value (e.g. never return 2 as '1 + 1' or 'aaaaa' as 'a' * 5)."


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


def clean_llm_output(response: str):
    return remove_ending_commas_in_list(
        remove_comments(remove_output_schema_from_response(response))
    )


def parse_llm_output(
    output_parser, response: str, model: str, default={}, verbose: bool = False
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
                llm=ChatOpenAI(model_name=model, temperature=0),
            )
            try:
                return output_fixing_parser.parse(response)
            except:
                logger.info("OutputParser exception")
                logger.info(response)
                logger.info(traceback.format_exc())
                return default


def get_parsed_output_dict(
    output_parser, llm_output, parse_by_alias: bool, model: str, verbose: bool = False
) -> Dict:
    """Use the output parser to parse the LLM output and return the parsed output as a dictionary"""
    pred = parse_llm_output(output_parser, llm_output, model=model, verbose=verbose)

    if isinstance(pred, BaseModel):
        pred_dict = pred.dict(by_alias=parse_by_alias)
    else:
        pred_dict = pred

    if isinstance(pred_dict, list):
        # sometimes the LLM outputs a list of JSONs instead of one JSON
        pred_dict = pred_dict[0]

    return pred_dict


@backoff.on_exception(backoff.expo, Exception, max_tries=5, factor=2)
async def call_openai_chat_model(
    messages: List,
    model: str,
    max_tokens: int,
    verbose: bool = False,
    # message_format: str = "langchain",
    # labels: str = [],
    **kwargs,
):
    # llm_pricing_calculator = LLMPricingCalculator()

    # if message_format != "langchain":
    # messages = get_messages_in_langchain_format(messages)

    common_model_args = {
        "temperature": 0,
        "max_tokens": max_tokens,
    }

    input_tokens = 0
    output_tokens = 0
    total_cost = 0

    # if kwargs.get("model_type") == "bedrock":
    #     from langchain_aws import ChatBedrock
    #     from llm_utils.callbacks import BedrockHandler

    #     # TODO: make this generic so that it works inside the deployed instance too
    #     os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
    #     callback = BedrockHandler()

    #     llm = ChatBedrock(
    #         credentials_profile_name="crossaccount",
    #         model_id=model,
    #         model_kwargs=common_model_args,
    #         callbacks=[callback],
    #     )
    #     ai_response = await llm.ainvoke(messages)
    #     input_tokens, output_tokens, total_cost = get_llm_metrics_for_custom_model(
    #         llm, model, messages, ai_response
    #     )

    # elif kwargs.get("model_type") == "anthropic":
    #     from langchain_anthropic import ChatAnthropic

    #     # import anthropic

    #     # TODO: need to set ANTHROPIC_API_KEY env var
    #     llm = ChatAnthropic(
    #         model=model,
    #         **common_model_args,
    #     )
    #     ai_response = await llm.ainvoke(messages)
    #     # client = anthropic.Anthropic(
    #     # defaults to os.environ.get("ANTHROPIC_API_KEY")
    #     # api_key=os.environ['ANTHROPI'],
    #     # )

    #     input_tokens, output_tokens, total_cost = get_llm_metrics_for_custom_model(
    #         llm, model, messages, ai_response
    #     )

    # else:
    openai_model_kwargs = {
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
    }
    llm = ChatOpenAI(model=model, **common_model_args, **openai_model_kwargs)
    # if not kwargs.get("skip_token_limit_check"):
    #     messages = correct_token_limit_in_messages(
    #         messages, llm, max_tokens, labels
    #     )

    # TODO: support token counting for fine-tuned models
    with get_openai_callback() as llm_callback:
        ai_response = await llm.ainvoke(messages)
        input_tokens = llm_callback.prompt_tokens
        output_tokens = llm_callback.completion_tokens
        total_cost = llm_callback.total_cost

    ai_response = ai_response.content

    # observability_logger = ObservabilityLogger()
    # observability_logger.log_event_to_queue(
    #     {
    #         "operation": "llm",
    #         "input_tokens": input_tokens,
    #         "output_tokens": output_tokens,
    #         "total_cost": total_cost,
    #         "labels": labels,
    #     }
    # )

    # log number of input and output tokens for pricing
    # llm_pricing_calculator.add(
    #     LLMInvocation(
    #         model=model,
    #         input_tokens=input_tokens,
    #         output_tokens=output_tokens,
    #         labels=labels,
    #         cost=total_cost,
    #     )
    # )

    # import ipdb

    # ipdb.set_trace()

    if verbose:
        logger.info(
            f"model: {model} prompt: {messages} response: {ai_response} input tokens: {input_tokens} output tokens: {output_tokens}"
        )

    return ai_response


async def call_llm_and_parse_output(
    messages,
    model,
    output_parser,
    max_tokens,
    # labels,
    verbose: bool = False,
    parse_by_alias: bool = False,
    **kwargs,
):
    llm_output = await call_openai_chat_model(
        messages,
        model=model,
        max_tokens=max_tokens,
        # labels=labels,
        verbose=verbose,
        **kwargs,
    )
    return get_parsed_output_dict(
        output_parser,
        llm_output,
        parse_by_alias=parse_by_alias,
        model=model,
        verbose=verbose,
    )
