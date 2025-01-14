import traceback
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from lib.llm import (
    call_llm_and_parse_output,
    get_llm_input_messages,
    COMMON_INSTRUCTIONS,
    logger,
)


async def generate_answer_for_task(
    task_name: str, task_description: str, task_context: str, model: str, api_key: str
) -> str:
    system_prompt_template = """You are a helpful and encouraging tutor.\n\n{input_description}\n\nYou need to work out your own solution to the task. You will use this solution later to evaluate the student's solution.\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description and completely adhere to the requirements without making up anything on your own that is not already present in the description.{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name:\n```\n{task_name}\n```\n\nTask description:\n```\n{task_description}\n```"""
    llm_input_kwargs = {}
    input_description = "You will be given a task that has been assigned to a student along with its description."

    if task_context:
        user_prompt_template += f"""\n\nContext:\n```\n{task_context}\n```"""
        llm_input_kwargs["task_context"] = task_context
        input_description = "You will be given a task that has been assigned to a student along with its description and the context required to solve it."

    class Output(BaseModel):
        solution: str = Field(
            title="solution",
            description="The solution to the task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        input_description=input_description,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
        **llm_input_kwargs,
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model,
            output_parser=output_parser,
            api_key=api_key,
            max_tokens=2048,
            verbose=True,
            labels=["generate_answer"],
        )
        return pred_dict["solution"]
    except Exception as exception:
        traceback.print_exc()
        raise exception


def convert_tests_to_prompt(tests: List[Dict]) -> str:
    if not tests:
        return ""

    return "\n-----------------\n".join(
        [f"Input:\n{test['input']}\n\nOutput:\n{test['output']}" for test in tests]
    )


async def generate_tests_for_task_from_llm(
    task_name: str,
    task_description: str,
    task_context: str,
    num_test_inputs: int,
    tests: List[Dict],
    model: str,
    api_key: str,
):
    system_prompt_template = """You are a test case generator for programming tasks.\n\n{input_description}\n\nYou need to generate a list of test cases in the form of input/output pairs.\n\n- Give some reasoning before arriving at the answer but keep it concise.\n- Create diverse test cases that cover various scenarios, including edge cases.\n- Ensure the test cases are relevant to the task description.\n- Provide at least 3 test cases, but no more than 5.\n- Ensure that every test case is unique.\n- If you are given a list of test cases, you need to ensure that the new test cases you generate are not duplicates of the ones in the list.\n{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name:\n```\n{task_name}\n```\n\nTask description:\n```\n{task_description}\n```\n\nNumber of inputs: {num_test_inputs}\n\nTest cases:\n```\n{tests}\n```"""
    llm_input_kwargs = {}
    input_description = "You will be given a task name, its description, the number of inputs expected and, optionally, a list of test cases."

    if task_context:
        user_prompt_template += f"""\n\nContext:\n```\n{task_context}\n```"""
        llm_input_kwargs["task_context"] = task_context
        input_description = "You will be given a task name, its description, the number of inputs expected, the context required to solve the task and, optionally, a list of test cases."

    class TestCase(BaseModel):
        input: List[str] = Field(
            description="The list of inputs for a single test case. The number of inputs is {num_test_inputs}. Always return a list"
        )
        output: str = Field(description="The expected output for the test case")
        description: str = Field(
            description="A very brief description of the test case", default=""
        )

    class Output(BaseModel):
        test_cases: List[TestCase] = Field(
            description="A list of test cases for the given task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    # import ipdb; ipdb.set_trace()

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        input_description=input_description,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
        num_test_inputs=num_test_inputs,
        tests=convert_tests_to_prompt(tests),
        **llm_input_kwargs,
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model,
            output_parser=output_parser,
            api_key=api_key,
            max_tokens=2048,
            verbose=True,
        )
        return [
            {
                "input": tc["input"],
                "output": tc["output"],
                "description": tc["description"],
            }
            for tc in pred_dict["test_cases"]
        ]
    except Exception as exception:
        traceback.print_exc()
        raise exception
