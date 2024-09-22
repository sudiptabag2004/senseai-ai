class MessageHistory:
    def __init__(self):
        self._messages = []

    def add_user_message(self, message):
        self._messages.append({"role": "user", "content": message})

    def add_ai_message(self, message):
        self._messages.append({"role": "assistant", "content": message})

    def add_messages(self, messages):
        self._messages.extend(messages)

    @property
    def messages(self):
        return self._messages

    def clear(self):
        self._messages = []