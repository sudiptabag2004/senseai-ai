from langchain.prompts.prompt import PromptTemplate

EXTRACT_ANSWER = """Instructions:
--------------
{instructions}
--------------
Completion:
--------------
{completion}
--------------

Above, either the Completion did not satisfy the constraints given in the Instructions or the completion did satisfy the constraints but included other information as well.
Error:
--------------
{error}
--------------

If the Completion contains a value in the format specified in the Instructions, simply extract that value from the Completion without modifying it.
If the Completion doesn't contain any valid value, please try again and respond with an answer that satisfies the constraints laid out in the Instructions:"""


EXTRACT_ANSWER_PROMPT = PromptTemplate.from_template(EXTRACT_ANSWER)
