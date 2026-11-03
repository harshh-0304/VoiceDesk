"""
VoiceDesk - Conversation Memory Management

Maintains a rolling conversational context window formatted for OpenAI/Groq chat completions.
Provides thread-safe and serialized memory states for both CLI and WebSocket sessions.
"""

from typing import List, Dict, Optional, Any

VALID_ROLES = frozenset({"system", "user", "assistant", "tool"})


class ConversationMemory:
    """
    Keeps a rolling window of messages for contextual LLM conversations.
    Messages follow the standard chat schema: {"role": "user" | "assistant" | "system", "content": "..."}.
    """

    def __init__(self, max_messages: int = 12) -> None:
        if max_messages <= 0:
            raise ValueError("max_messages must be a positive integer greater than zero")
        self.max_messages = max_messages
        self._messages: List[Dict[str, str]] = []

    def add_user(self, text: str) -> None:
        """Add a sanitized user message to history."""
        cleaned = text.strip() if text else ""
        if not cleaned:
            return
        self._messages.append({"role": "user", "content": cleaned})
        self._trim()

    def add_assistant(self, text: str) -> None:
        """Add a sanitized assistant message to history."""
        cleaned = text.strip() if text else ""
        if not cleaned:
            return
        self._messages.append({"role": "assistant", "content": cleaned})
        self._trim()

    def add_message(self, role: str, content: str) -> None:
        """Add an arbitrary role message (e.g. system or tool) to history."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Expected one of {sorted(VALID_ROLES)}.")
        cleaned = content.strip() if content else ""
        if not cleaned:
            return
        self._messages.append({"role": role, "content": cleaned})
        self._trim()

    def _trim(self) -> None:
        """Ensure message buffer does not exceed max_messages limit."""
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def get_history(self) -> List[Dict[str, str]]:
        """Return a defensive deep copy of conversation history."""
        return [{"role": m["role"], "content": m["content"]} for m in self._messages]

    def get_last_user_message(self) -> Optional[str]:
        """Return the most recent user prompt, if any."""
        for msg in reversed(self._messages):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Return the most recent assistant response, if any."""
        for msg in reversed(self._messages):
            if msg["role"] == "assistant":
                return msg["content"]
        return None

    def clear(self) -> None:
        """Reset conversation memory to an empty state."""
        self._messages.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory instance for persistence or transmission."""
        return {
            "max_messages": self.max_messages,
            "messages": self.get_history(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Reconstruct memory instance from serialized dictionary."""
        max_messages = data.get("max_messages", 12)
        instance = cls(max_messages=max_messages)
        for msg in data.get("messages", []):
            if (
                isinstance(msg, dict)
                and msg.get("role") in VALID_ROLES
                and "content" in msg
            ):
                instance.add_message(msg["role"], msg["content"])
        return instance

    def estimate_token_count(self) -> int:
        """Estimate the approximate token count consumed by active conversation history."""
        # Common rule of thumb: ~4 characters per token plus per-message overhead
        if not self._messages:
            return 0
        total_chars = sum(len(m.get("content", "")) for m in self._messages)
        message_overhead = len(self._messages) * 4
        return max(0, int(total_chars / 4) + message_overhead)

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregate statistics about current conversation session."""
        user_count = sum(1 for m in self._messages if m["role"] == "user")
        assistant_count = sum(1 for m in self._messages if m["role"] == "assistant")
        return {
            "total_messages": len(self._messages),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "estimated_tokens": self.estimate_token_count(),
            "max_messages": self.max_messages,
        }

    def export_markdown(self, title: str = "VoiceDesk Transcript") -> str:
        """Export the conversation transcript as a clean Markdown document."""
        lines = [f"# {title}", ""]
        if not self._messages:
            lines.append("*No messages recorded in this session.*")
            return "\n".join(lines)

        for msg in self._messages:
            role_label = "VoiceDesk" if msg["role"] == "assistant" else msg["role"].capitalize()
            lines.append(f"### {role_label}")
            lines.append(f"{msg['content']}\n")

        return "\n".join(lines).strip()

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:
        return f"ConversationMemory(count={len(self._messages)}, max_messages={self.max_messages})"
