from typing import Union


class Subject:
    def __init__(self, subject_name: str, topic_tree: dict = None):
        self.subject_name = subject_name
        if topic_tree is None:
            self.topic_tree = self.generate_topic_tree()
        else:
            self.topic_tree = topic_tree

        for topic in self.topic_tree:
            if "learing_outcomes" not in topic_tree[topic]:
                topic_tree[topic][
                    "learning_outcomes"
                ] = self.generate_learning_outcomes(topic)

    def generate_learning_outcomes(self, topic):
        pass

    def generate_topic_tree(self):
        pass
