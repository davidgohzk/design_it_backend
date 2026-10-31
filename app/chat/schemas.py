"""Request models for /api/chat."""

from typing import Literal

from pydantic import Field, model_validator

from ..cases import CaseId
from ..schemas import StrictModel

MAX_CHAT_CHARS = 120_000


class ChatTurn(StrictModel):
    # "system" is deliberately not accepted: the server owns the system prompt.
    role: Literal["user", "assistant"]
    content: str = Field(max_length=32_000)
    # Structured mode: the fact ids the server returned for this client turn.
    disclosedFactIds: list[str] | None = Field(default=None, max_length=50)


class ChatRequest(StrictModel):
    caseId: CaseId
    messages: list[ChatTurn] = Field(min_length=1, max_length=100)
    # False keeps the plain text stream; True returns {reply, disclosedFactIds, guard} (WP2).
    structured: bool = False

    @model_validator(mode="after")
    def check_conversation(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last message must come from the user.")
        if sum(len(turn.content) for turn in self.messages) > MAX_CHAT_CHARS:
            raise ValueError("The conversation is too long.")
        return self
