import traceback
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from lib.llm import (
    call_llm_and_parse_output,
    get_llm_input_messages,
    COMMON_INSTRUCTIONS,
    logger,
)


async def generate_answer_for_task(
    task_name: str, task_description: str, model: str
) -> str:
    system_prompt_template = """You are a helpful and encouraging tutor.\n\nYou will be given a task that has been assigned to a student along with its description.\n\nYou need to work out your own solution to the task. You will use this solution later to evaluate the student's solution.\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description and completely adhere to the requirements without making up anything on your own that is not already present in the description.{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = (
        """Task name: {task_name}\n\nTask description: {task_description}"""
    )

    class Output(BaseModel):
        solution: str = Field(
            title="solution",
            description="The solution to the task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model,
            output_parser=output_parser,
            max_tokens=2048,
            verbose=True,
            labels=["generate_answer"],
        )
        return pred_dict["solution"]
    except Exception as exception:
        traceback.print_exc()
        raise exception
