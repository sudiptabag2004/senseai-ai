from langchain import PromptTemplate

system_template = """You are EduGPT a very helpful and effective assistant for facilitating the various processes in education. You are very experienced in the field of education and are adept at the following:
- Breaking down any course content into objective learning outcomes to help structure anyone's learning journey as much as possible.
- Explaining any concept of any difficulty in the simplest way to ensure a learner understands it.
- Figuring out excellent learning and evaluation strategies to monitor and maintain good learning growth.
"""

create_learning_outcomes_template_text = """Please create learning outcomes for the following subject and topic:

Subject: {subject}
Topic: {topic}

Here are some guidelines on how to create Learning Outcomes:
- Learning Outcomes are measurable statements that articulate at the beginning what students should know, be able to do, or value as a result of taking a course or completing a program (also called Backwards Course Design)
- Learning Outcomes take the form: (action verb) (learning statement)
- Learning Outcomes should be specific, measurable, aligned with the subject, realistic and achievable.
- Avoid verbs that are unclear and cannot be observed and measured easily, for example: appreciate, become aware of, become familiar with, know, learn, and understand.
- The Learning Outcomes should exhaustively cover the given topic

We need to create the learning outcomes with respect to Bloom's Taxonomy which provides some useful verbs to represent the learning outcomes for different levels of learning. The following are the levels of Bloom's Taxonomy:

1. Remember
- Retrieving, recognizing, and recalling relevant knowledge/facts from long‐term memory
- Action Verbs: list, recite, outline, define, name, match, quote, recall, identify, label, recognize

2. Understand
- Constructing meaning from oral, written, and graphic messages through interpreting, exemplifying, classifying, summarizing, inferring, comparing, and explaining.
- Action Verbs: describe, explain, paraphrase, restate, give original examples of, summarize, contrast, interpret, discuss.

3. Apply
- Carrying out or using a procedure for executing, or implementing.
- Action Verbs: calculate, predict, apply, solve, illustrate, use, demonstrate, determine, model, perform, present.

4. Analyze
- Breaking material into constituent parts, determining how the parts relate to one another and to an overall structure or purpose through differentiating, organizing, and attributing.
- Action Verbs: classify, break down, categorize, analyze, diagram, illustrate, criticize, simplify, associate.

5. Evaluate
- Making judgments based on criteria and standards through checking and critiquing.
- Action Verbs: choose, support, relate, determine, defend, judge, grade, compare, contrast, argue, justify, support, convince, select, evaluate.

6. Create
- Putting elements together to form a coherent or functional whole; reorganizing elements into a new pattern or structure through generating, planning, or producing.
- Action Verbs: design, formulate, build, invent, create, compose, generate, derive, modify, develop.

We do not need to have the same number of learning outcomes for each of these Bloom Levels.
"""
create_learning_outcomes_template = PromptTemplate.from_template(
    create_learning_outcomes_template_text
)

parse_learning_outcomes_template_text = """
{raw_learning_outcomes}

Please parse the learning outcomes into a JSON the following format:
{{
    "Remember": [
        "Learning Outcome 1",
        "Learning Outcome 2",
        ...
    ],
    "Understand": [
        "Learning Outcome 1",
        "Learning Outcome 2",
        ...
    ],
    ...
}}

JSON:"""
parse_learning_outcomes_template = PromptTemplate.from_template(
    parse_learning_outcomes_template_text
)
