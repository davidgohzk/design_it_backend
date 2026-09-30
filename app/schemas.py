from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .assess_prompts import ASSESS_SECTIONS
from .prompts import PERSONAS

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
    # caseId and mode are omitted by /demo, which keeps the original diagram prompt.
    caseId: CaseId = "brightpath"
    mode: Literal["sketch", "final"] | None = None
    prompt: str = Field(min_length=1, max_length=8_000)
    currentCode: str | None = Field(default=None, max_length=20_000)
    # Sketch mode: the node IDs and labels already used in other sketches, one per line.
    context: str | None = Field(default=None, max_length=20_000)
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


AssessTask = Literal["evidence", "match", "soundness"]


class AssessFact(StrictModel):
    id: str = Field(max_length=100)
    label: str = Field(max_length=500)
    detail: str = Field(max_length=2_000)
    disclosure: Literal["given", "on-ask", "on-probe"]
    # Evidence task only: false when no client message contains any of the fact's cues.
    checkSurfaced: bool | None = None


class AssessRequest(StrictModel):
    caseId: CaseId
    task: AssessTask
    facts: list[AssessFact] = Field(min_length=1, max_length=50)
    # Task-specific evidence (transcript, design doc, pairs, ...). Sent to the model as data only.
    evidence: dict[str, Any]
    retrySections: list[str] | None = Field(default=None, min_length=1, max_length=4)

    @model_validator(mode="after")
    def check_request(self) -> "AssessRequest":
        expected = [fact_id for fact_id, _detail in PERSONAS[self.caseId]["facts"]]
        if [fact.id for fact in self.facts] != expected:
            raise ValueError("The fact ids don't match this case's facts.")
        if self.retrySections and not set(self.retrySections) <= set(ASSESS_SECTIONS[self.task]):
            raise ValueError(f"retrySections must be sections of the {self.task} task.")
        return self


class AssessResponse(BaseModel):
    content: str
    model: str
    promptVersion: str
