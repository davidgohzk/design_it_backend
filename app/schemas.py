from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_CHAT_CHARS = 120_000

# Cases with a persona on the server. "brightpath" is the /demo case and the default.
CaseId = Literal["brightpath", "community-room"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatTurn(StrictModel):
    # "system" is deliberately not accepted: the server owns the system prompt.
    role: Literal["user", "assistant"]
    content: str = Field(max_length=32_000)


class ChatRequest(StrictModel):
    caseId: CaseId = "brightpath"
    messages: list[ChatTurn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_conversation(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("The last message must come from the user.")
        if sum(len(turn.content) for turn in self.messages) > MAX_CHAT_CHARS:
            raise ValueError("The conversation is too long.")
        return self


class PriorAttempt(StrictModel):
    code: str = Field(min_length=1, max_length=20_000)
    error: str = Field(max_length=8_000)


class DiagramRequest(StrictModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    currentCode: str | None = Field(default=None, max_length=20_000)
    priorAttempt: PriorAttempt | None = None


class ChecklistItem(StrictModel):
    id: str = Field(max_length=100)
    label: str = Field(max_length=500)
    description: str = Field(max_length=2_000)


class TranscriptItem(StrictModel):
    id: str = Field(max_length=50)
    role: Literal["system", "user", "assistant"]
    content: str = Field(max_length=40_000)


ReviewSection = Literal["claims", "omissions", "coverage", "reasoning", "critique"]


class ReviewRequest(StrictModel):
    # Field order matches the frontend's JSON.stringify payload so the model sees identical text.
    coverageChecklist: list[ChecklistItem] = Field(max_length=50)
    caseBrief: str = Field(max_length=200_000)
    transcript: list[TranscriptItem] = Field(max_length=300)
    soapReport: str = Field(max_length=200_000)
    extractedReferences: list[dict[str, Any]] = Field(max_length=500)
    # Partial retry only: the sections to redo, plus already-accepted claims so claim indexes stay valid.
    retrySections: list[ReviewSection] | None = Field(default=None, min_length=1, max_length=5)
    acceptedClaims: list[dict[str, Any]] | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_retry(self) -> "ReviewRequest":
        if self.acceptedClaims is not None and (not self.retrySections or "claims" in self.retrySections):
            raise ValueError("acceptedClaims is only allowed when retrying sections other than claims.")
        return self


class ReviewResponse(BaseModel):
    content: str
