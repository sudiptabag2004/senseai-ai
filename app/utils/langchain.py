from typing import List
import sys

if "../" not in sys.path:
    sys.path.append("../")

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from models import ChatMarkupLanguage


def convert_cml_to_langchain_format(message: ChatMarkupLanguage):
    if message.role == "assistant":
        message_cls = AIMessage
    elif message.role == "user":
        message_cls = HumanMessage
    else:
        message_cls = SystemMessage

    return message_cls(content=message.content)


def convert_cml_messages_to_langchain_format(
    messages: List[ChatMarkupLanguage],
    ignore_types: List[str] = ["irrelevant"],
):
    """
    1. Ignore messages of type present in ignore_types by users and their corresponding AI responses
    2. Convert ChatMarkupLanguage messages to langchain message schema
    """

    relevant_messages = []
    index = 0
    while index < len(messages):
        if messages[index].type in ignore_types:
            # ignore both the current user response message and the corresponding AI response message
            index += 2
            continue

        relevant_messages.append(messages[index])
        index += 1

    return [convert_cml_to_langchain_format(message) for message in relevant_messages]
