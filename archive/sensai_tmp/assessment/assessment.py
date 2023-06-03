from typing import Literal
from langchain.llms import OpenAI
import openai

# from sensai.subject import Subject
from .prompts import (
    create_assessment_question,
    chat_assessment_system,
    chat_assessment_start,
)


class Assessment:
    def __init__(
        self,
        subject: str = None,
        topic: str = None,
        learning_outcome: str = None,
        bloom_level: Literal[
            "remember", "understand", "apply", "analyse", "evaluate", "create"
        ] = None,
        mode: Literal["single_lo"] = "single_lo",
    ):
        self.subject = subject
        self.topic = topic
        self.learning_outcome = learning_outcome
        self.bloom_level = bloom_level
        self.mode = mode

        self.assessment_data = {
            "started": False,
            "chat_history": [],
            "finished": False,
            "result": None,
        }
        # self.llm = OpenAI()

    def set_subject(self, subject: str):
        self.subject = subject

    def set_topic(self, topic: str):
        assert (
            topic in self.subject.topic_tree.keys()
        ), f"Topic {topic} not found in subject {self.subject.subject_name}"
        self.config.topic = topic

    def set_learning_outcome(self, learning_outcome: str):
        assert self.config.topic is not None, "Topic not set"
        assert (
            learning_outcome
            in self.subject.topic_tree[self.config.topic]["learning_outcomes"]
        ), f"Learning outcome {learning_outcome} not found in topic {self.config.topic}"
        self.config.learning_outcome = learning_outcome

    def set_bloom_level(
        self,
        bloom_level: Literal[
            "remember", "understand", "apply", "analyse", "evaluate", "create"
        ],
    ):
        assert bloom_level in [
            "remember",
            "understand",
            "apply",
            "analyse",
            "evaluate",
            "create",
        ], f"Bloom level {bloom_level} not recognised"
        self.config.bloom_level = bloom_level

    def create_assessment_question(self):
        assert self.config.topic is not None, "Topic not set"
        assert (
            self.config.learning_outcome is not None
        ), "Learning outcome not set"
        assert self.config.bloom_level is not None, "Bloom level not set"

        if self.config.mode == "single_lo":
            prompt = create_assessment_question(
                learning_outcome=self.config.learning_outcome
            )
            response = self.llm(prompt)
        else:
            raise NotImplementedError(
                f"Mode {self.config.mode} not implemented yet"
            )

        return response

    def call_llm_for_chat(self, messages=None):
        if messages is None:
            messages = self.assessment_data["chat_history"]

        response = openai.ChatCompletion.create(
            model="gpt-4", messages=messages, temperature=0
        )

        return response["choices"][0]["message"]["content"].strip()

    def chat(self, learner_message: str = None):
        if self.assessment_data["started"] == False:
            self.assessment_data["started"] = True
            self.assessment_data["chat_history"] = []
            self.assessment_data["finished"] = False

        if self.assessment_data["finished"] == True:
            raise Exception("Assessment already finished")

        if len(self.assessment_data["chat_history"]) == 0:
            system_prompt = chat_assessment_system.format(
                subject=self.subject,
                topic=self.topic,
                learning_outcome=self.learning_outcome,
            )
            self.assessment_data["chat_history"].append(
                {"role": "system", "content": system_prompt}
            )

            chat_assessment_start_message = chat_assessment_start.format(
                subject=self.subject,
                topic=self.topic,
                learning_outcome=self.learning_outcome,
            )
            self.assessment_data["chat_history"].append(
                {"role": "user", "content": chat_assessment_start_message}
            )

            chat_assessment_response = self.call_llm_for_chat()
            self.assessment_data["chat_history"].append(
                {"role": "assistant", "content": chat_assessment_response}
            )

            return chat_assessment_response

        self.assessment_data["chat_history"].append(
            {"role": "user", "content": learner_message}
        )

        chat_assessment_response = self.call_llm_for_chat()
        self.assessment_data["chat_history"].append(
            {"role": "assistant", "content": chat_assessment_response}
        )

        if "[END]" in chat_assessment_response:
            self.assessment_data["finished"] = True
            if "[0]" in chat_assessment_response:
                self.assessment_data["result"] = 0
            elif "[1]" in chat_assessment_response:
                self.assessment_data["result"] = 1
            elif "[2]" in chat_assessment_response:
                self.assessment_data["result"] = 2

            chat_assessment_response = chat_assessment_response[
                : chat_assessment_response.find("[END]")
            ].strip()

        return chat_assessment_response
