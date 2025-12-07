# Placeholder code
from typing import List, Dict


class ConversationMemory:
    """
    Keeps a rolling window of the conversation for better LLM context.
    Stores messages in OpenAI chat format: {"role": "...", "content": "..."}.
    """

    def __init__(self, max_messages: int = 12) -> None:
        self.max_messages = max_messages
        self._messages: List[Dict[str, str]] = []

    def add_user(self, text: str) -> None:
        if not text:
            return
        self._messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, text: str) -> None:
        if not text:
            return
        self._messages.append({"role": "assistant", "content": text})
        self._trim()

    def _trim(self) -> None:
        if len(self._messages) > self.max_messages:
            # keep only the last N messages
            self._messages = self._messages[-self.max_messages :]

    def get_history(self) -> List[Dict[str, str]]:
        return list(self._messages)
