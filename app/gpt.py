import logging
import pathlib
import os
from os.path import dirname
from typing import List, Dict
import queue
import threading

import backoff
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import OutputFixingParser
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage, BaseOutputParser
from langchain.prompts import (
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain.callbacks.base import BaseCallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

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


class ThreadedGenerator:
    def __init__(self):
        self.queue = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration:
            raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)


class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen

    def on_llm_new_token(self, token: str, **kwargs):
        self.gen.send(token)


def llm_thread(
    threaded_generator,
    messages: List,
    chat_model_init_kwargs: Dict,
    callbacks: List = [],
):
    try:
        chat = ChatOpenAI(
            callback_manager=BaseCallbackManager(
                [ChainStreamHandler(threaded_generator)]
            ),
            **chat_model_init_kwargs,
        )
        chat(messages, callbacks=callbacks)

    finally:
        threaded_generator.close()


def stream_chat_model_response(
    messages: List, chat_model_init_kwargs: Dict, callbacks: List = []
):
    threaded_generator = ThreadedGenerator()
    threading.Thread(
        target=llm_thread,
        args=(threaded_generator, messages, chat_model_init_kwargs, callbacks),
    ).start()
    return threaded_generator


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def call_openai_chat_model(
    messages: List,
    model: str,
    max_tokens: int,
    callbacks: List = [],
    streaming: bool = False,
):
    chat_model_init_kwargs = {
        "model_name": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "model_kwargs": {
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        },
        "streaming": streaming,
    }

    if streaming:
        return stream_chat_model_response(
            messages, chat_model_init_kwargs, callbacks=callbacks
        )

    chat_model = ChatOpenAI(
        model_name=model,
        temperature=0,
        max_tokens=max_tokens,
        model_kwargs={
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        },
        streaming=streaming,
    )
    response = chat_model(messages, callbacks=callbacks)

    logging.info(
        f"model: {model} prompt: {messages} response: {response.content} max tokens: {max_tokens}"
    )
    return response.content


# @backoff.on_exception(backoff.expo, Exception, max_tries=3)
def run_openai_chat_chain(
    user_prompt_template: str,
    user_message: str,
    system_prompt: str,
    messages: List[ChatMarkupLanguage],
    output_parser: BaseOutputParser = None,
    ignore_types: List[str] = ["irrelevant"],
    model: str = "gpt-4",
    verbose: bool = False,
    callbacks: List = [],
):
    chat_model = ChatOpenAI(temperature=0, model=model)
    # langchain_messages = [SystemMessage(content=system_prompt)]
    langchain_messages = []
    if messages:
        langchain_messages.extend(
            convert_cml_messages_to_langchain_format(messages, ignore_types)
        )

    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.messages = langchain_messages

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template(user_prompt_template),
        ]
    )

    chat_chain = ConversationChain(
        llm=chat_model,
        memory=memory,
        prompt=chat_prompt_template,
        verbose=verbose,
        callbacks=callbacks,
    )

    response = chat_chain.run(user_message)

    if output_parser:
        response = parse_llm_output(output_parser, response, model=model)

    return response
