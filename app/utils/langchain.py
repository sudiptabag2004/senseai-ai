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


def convert_cml_messages_to_langchain_format(messages: List[ChatMarkupLanguage]):
    return [convert_cml_to_langchain_format(message) for message in messages]
