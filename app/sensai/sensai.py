import json
import openai

from .prompts import (
    system_template,
    create_learning_outcomes_template,
    parse_learning_outcomes_template,
)

openai.api_key = "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"


def create_learning_outcomes(subject: str, topic: str):
    lo_template = create_learning_outcomes_template.format(
        subject=subject, topic=topic
    )
    messages = [
        {"role": "system", "content": system_template},
        {"role": "user", "content": lo_template},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4", messages=messages, temperature=0, max_tokens=1024
    )
    raw_learning_outcomes = response["choices"][0]["message"]["content"].strip()

    parse_lo_template = parse_learning_outcomes_template.format(
        raw_learning_outcomes=raw_learning_outcomes
    )
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=parse_lo_template,
        temperature=0,
        max_tokens=1024,
    )

    learning_outcomes = response["choices"][0]["text"].strip()
    learning_outcomes = json.loads(learning_outcomes)

    return learning_outcomes

def start_assessment()
