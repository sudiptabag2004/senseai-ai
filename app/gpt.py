import logging
import pathlib
import os
from os.path import dirname
from typing import List

import backoff
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import OutputFixingParser
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage, BaseOutputParser

from models import ChatMarkupLanguage
from utils.langchain import convert_cml_messages_to_langchain_format

root_dir = pathlib.Path(__file__).parent.resolve()
log_save_path = f"{root_dir}/logs/gpt-logs/1"
os.makedirs(dirname(log_save_path), exist_ok=True)

logging.basicConfig(
    filename=log_save_path,
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)


def parse_llm_output(output_parser, response, model, default={}):
    try:
        return output_parser.parse(response)
    except:
        output_fixing_parser = OutputFixingParser.from_llm(
            parser=output_parser, llm=ChatOpenAI(model_name=model, temperature=0)
        )
        try:
            return output_fixing_parser.parse(response)
        except:
            return default


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def call_openai_chat_model(
    messages: List, model: str, max_tokens: int, callbacks: List = []
):
    chat_model = ChatOpenAI(
        model_name=model,
        temperature=0,
        max_tokens=max_tokens,
        model_kwargs={
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        },
    )
    response = chat_model(messages, callbacks=callbacks)

    logging.info(
        f"model: {model} prompt: {messages} response: {response.content} max tokens: {max_tokens}"
    )
    return response.content


# @backoff.on_exception(backoff.expo, Exception, max_tries=3)
def run_openai_chat_chain(
    input: str,
    system_prompt: str,
    messages: List[ChatMarkupLanguage],
    output_parser: BaseOutputParser = None,
    model: str = "gpt-4",
    verbose: bool = False,
    callbacks: List = [],
):
    chat_model = ChatOpenAI(temperature=0, model=model)
    langchain_messages = [SystemMessage(content=system_prompt)]
    if messages:
        langchain_messages.extend(convert_cml_messages_to_langchain_format(messages))

    memory = ConversationBufferMemory()
    memory.chat_memory.messages = langchain_messages

    chat_chain = ConversationChain(
        llm=chat_model, memory=memory, verbose=verbose, callbacks=callbacks
    )

    response = chat_chain.run(input)

    if output_parser:
        response = parse_llm_output(output_parser, response, model=model)

    return response
