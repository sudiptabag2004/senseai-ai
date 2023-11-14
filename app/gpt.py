import logging
import pathlib
import json
import traceback
import asyncio
import os
from os.path import dirname
from typing import List, Dict, AsyncIterable
import queue
import threading

import backoff
import langchain
from pydantic import BaseModel
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
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from settings import settings
from models import ChatMarkupLanguage
from prompts import EXTRACT_ANSWER_PROMPT
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

from gptcache import Cache
from gptcache.manager.factory import manager_factory
from gptcache.processor.pre import get_prompt

# from gptcache.embedding import LangChain
# from gptcache.adapter.langchain_models import LangChainChat

# from langchain.embeddings.openai import OpenAIEmbeddings
# from gptcache.similarity_evaluation.distance import SearchDistanceEvaluation
# from gptcache.manager import CacheBase, VectorBase, get_data_manager
from langchain.cache import GPTCache
import hashlib


# get the content(only question) form the prompt to cache
# def get_msg_func(data, **_):
#     return data.get("messages")[-1].content


# def get_hashed_name(name):
#     return hashlib.sha256(name.encode()).hexdigest()


def get_hashed_name(name):
    return hashlib.sha256(name.encode()).hexdigest()


def init_gptcache(cache_obj: Cache, llm: str):
    hashed_llm = get_hashed_name(llm)
    cache_obj.init(
        pre_embedding_func=get_prompt,
        data_manager=manager_factory(manager="map", data_dir=f"map_cache_{hashed_llm}"),
    )


langchain.llm_cache = GPTCache(init_gptcache)


# embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
# encoder = LangChain(embeddings=embeddings)
# cache_base = CacheBase("sqlite")
# vector_base = VectorBase("faiss", dimension=1536, top_k=3)
# data_manager = get_data_manager(cache_base, vector_base)

# # cache.init(pre_embedding_func=get_msg_func)
# cache.init(
#     pre_embedding_func=get_msg_func,
#     embedding_func=encoder.to_embeddings,
#     data_manager=data_manager,
#     similarity_evaluation=SearchDistanceEvaluation(),
# )

# cache.init(pre_embedding_func=get_msg_func)
# cache.set_openai_key()


def parse_llm_output(output_parser, response, model, default={}):
    try:
        return output_parser.parse(response)
    except:
        output_fixing_parser = OutputFixingParser.from_llm(
            parser=output_parser,
            llm=ChatOpenAI(model_name=model, temperature=0),
            prompt=EXTRACT_ANSWER_PROMPT,
        )
        try:
            return output_fixing_parser.parse(response)
        except:
            return default


def parse_llm_output_with_key(output_parser, response: str, key: str, default={}):
    try:
        return output_parser.parse(response)
    except:
        # search for key in the response
        key_search_index = response.find(key)

        if key_search_index == -1:
            return default

        # find the { bracket the appears right before the key
        json_start_index = response[:key_search_index].rfind("{")
        json_end_index = response[json_start_index:].rfind("}")
        valid_json_string = response[
            json_start_index : json_start_index + json_end_index + 1
        ]

        try:
            return json.loads(valid_json_string)
        except:
            return default


# class ThreadedGenerator:
#     def __init__(self):
#         self.queue = queue.Queue()

#     def __iter__(self):
#         return self

#     def __next__(self):
#         item = self.queue.get()
#         if item is StopIteration:
#             raise item
#         return item

#     def send(self, data):
#         self.queue.put(data)

#     def close(self):
#         self.queue.put(StopIteration)


# class ChainStreamHandler(StreamingStdOutCallbackHandler):
#     def __init__(self, gen):
#         super().__init__()
#         self.gen = gen

#     def on_llm_new_token(self, token: str, **kwargs):
#         print(token)
#         self.gen.send(token)


# def chat_model_thread(
#     chat_model: ChatOpenAI,
#     messages: List,
#     threaded_generator,
#     callbacks: List = [],
# ):
#     try:
#         chat_model(messages, callbacks=callbacks)

#     finally:
#         threaded_generator.close()


async def stream_chat_model_response(
    chat_model: ChatOpenAI, messages: List, async_callback: AsyncIteratorCallbackHandler
) -> AsyncIterable[str]:
    # ref: https://www.youtube.com/watch?v=Gn54EbU9mRg

    task = asyncio.create_task(chat_model.agenerate(messages=[messages]))

    try:
        async for token in async_callback.aiter():
            yield token
    except:
        traceback.print_exc()
    finally:
        async_callback.done.set()

    await task


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def call_openai_chat_model(
    messages: List,
    model: str,
    max_tokens: int,
    streaming: bool = False,
    cache: bool = False,
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
        "cache": cache,
    }

    if streaming:
        # threaded_generator = ThreadedGenerator()
        # chat_model_init_kwargs["callback_manager"] = BaseCallbackManager(
        #     [ChainStreamHandler(threaded_generator)]
        # )
        callback = AsyncIteratorCallbackHandler()
        chat_model_init_kwargs["callbacks"] = [callback]

    chat_model = ChatOpenAI(
        **chat_model_init_kwargs,
    )

    # if cache:
    #     chat_model = LangChainChat(chat=chat_model)

    if streaming:
        # return stream_chat_model_response(
        #     chat_model, messages, threaded_generator, callbacks=callbacks
        # )
        return stream_chat_model_response(chat_model, messages, async_callback=callback)

    response = chat_model(messages)

    logging.info(
        f"model: {model} prompt: {messages} response: {response.content} max tokens: {max_tokens}"
    )
    return response.content


def chat_chain_thread(
    chat_chain: ConversationChain,
    user_message: str,
    threaded_generator,
):
    try:
        chat_chain.run(user_message)

    finally:
        threaded_generator.close()


async def stream_chat_chain_response(
    chat_chain: ConversationChain,
    user_message: str,
    # threaded_generator: ThreadedGenerator,
    async_callback: AsyncIteratorCallbackHandler,
) -> AsyncIterable[str]:
    # threading.Thread(
    #     target=chat_chain_thread,
    #     args=(chat_chain, user_message, threaded_generator),
    # ).start()
    # return threaded_generator
    task = asyncio.create_task(chat_chain.arun(user_message))

    try:
        async for token in async_callback.aiter():
            # print(token)
            yield token
    except:
        traceback.print_exc()
    finally:
        async_callback.done.set()

    await task


def prepare_chat_chain(
    user_prompt_template: str,
    system_prompt: str,
    messages: List[ChatMarkupLanguage],
    model: str = "gpt-4-0613",
    ignore_types: List[str] = ["irrelevant"],
    max_tokens: int = 1024,
    streaming: bool = False,
    verbose: bool = False,
    callbacks: List = [],
    cache: bool = False,
    system_prompt_kwargs: Dict = {},
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
        "cache": cache,
        "callbacks": callbacks,
    }

    chat_model = ChatOpenAI(**chat_model_init_kwargs)

    # langchain_messages = [SystemMessage(content=system_prompt)]
    # import ipdb

    # ipdb.set_trace()

    langchain_messages = []
    if messages:
        langchain_messages.extend(
            convert_cml_messages_to_langchain_format(messages, ignore_types)
        )

    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.messages = langchain_messages

    if system_prompt_kwargs:
        system_prompt_template = SystemMessagePromptTemplate.from_template(
            system_prompt, template_format="jinja2"
        )
        system_prompt_template.prompt.template = (
            system_prompt_template.prompt.template.format(**system_prompt_kwargs)
        )
    else:
        system_prompt_template = SystemMessagePromptTemplate.from_template(
            system_prompt
        )

    chat_prompt_template = ChatPromptTemplate.from_messages(
        [
            system_prompt_template,
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template(user_prompt_template),
        ]
    )

    # import ipdb

    # ipdb.set_trace()

    chat_chain = ConversationChain(
        llm=chat_model, memory=memory, prompt=chat_prompt_template, verbose=verbose
    )

    return chat_chain, memory


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def run_openai_chat_chain(
    user_prompt_template: str,
    user_message: str,
    system_prompt: str,
    messages: List[ChatMarkupLanguage],
    output_parser: BaseOutputParser = None,
    ignore_types: List[str] = ["irrelevant"],
    model: str = "gpt-4-0613",
    verbose: bool = False,
    parse_llm_output_for_key: str = None,
    cache: bool = False,
    system_prompt_kwargs: Dict = {},
):
    chat_chain, memory = prepare_chat_chain(
        user_prompt_template,
        system_prompt,
        messages,
        model,
        ignore_types,
        verbose=verbose,
        cache=cache,
        system_prompt_kwargs=system_prompt_kwargs,
    )
    response = chat_chain.run(user_message)

    logging.info(
        f"model: {model} history: {memory.chat_memory.messages} query: {user_message} response: {response}"
    )

    if output_parser:
        if parse_llm_output_for_key:
            response = parse_llm_output_with_key(
                output_parser, response, parse_llm_output_for_key
            )
        else:
            response = parse_llm_output(output_parser, response, model=model)

    return response


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def stream_openai_chat_chain(
    user_prompt_template: str,
    user_message: str,
    system_prompt: str,
    messages: List[ChatMarkupLanguage],
    ignore_types: List[str] = ["irrelevant"],
    model: str = "gpt-4-0613",
    verbose: bool = False,
    cache: bool = False,
    system_prompt_kwargs: Dict = {},
):
    # threaded_generator = ThreadedGenerator()

    # for token in stream_start_tokens:
    #     threaded_generator.send(token)

    callback = AsyncIteratorCallbackHandler()
    # chat_model_init_kwargs["callbacks"] = [callback]

    # callback_manager = BaseCallbackManager([ChainStreamHandler(threaded_generator)])

    chat_chain, _ = prepare_chat_chain(
        user_prompt_template,
        system_prompt,
        messages,
        model,
        ignore_types,
        streaming=True,
        verbose=verbose,
        callbacks=[callback],
        cache=cache,
        system_prompt_kwargs=system_prompt_kwargs,
    )

    # response = chat_chain.run(user_message)

    return stream_chat_chain_response(chat_chain, user_message, callback)
