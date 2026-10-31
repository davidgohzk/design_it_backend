"""Request and response models for /api/assess.

The task list here is the contract with the browser: `AssessTask` must name exactly the tasks the
prompt registry defines, and a test asserts that.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ..cases import CaseId, case_fact_ids
from ..schemas import StrictModel
from .prompts import ASSESS_SECTIONS

AssessTask = Literal["match", "assertion", "justify", "fit", "suggest", "bano", "turns", "scenario_adequacy", "iso", "rationale"]


class AssessFact(StrictModel):
    id: str = Field(max_length=100)
    label: str = Field(max_length=500)
    detail: str = Field(max_length=2_000)
    disclosure: Literal["given", "on-ask", "on-probe"]


class AssessRequest(StrictModel):
    caseId: CaseId
    task: AssessTask
    facts: list[AssessFact] = Field(min_length=1, max_length=50)
    # Task-specific evidence (transcript, design doc, pairs, ...). Sent to the model as data only.
    evidence: dict[str, Any]
    retrySections: list[str] | None = Field(default=None, min_length=1, max_length=4)

    @model_validator(mode="after")
    def check_request(self) -> "AssessRequest":
        if [fact.id for fact in self.facts] != case_fact_ids(self.caseId):
            raise ValueError("The fact ids don't match this case's facts.")
        if self.retrySections and not set(self.retrySections) <= set(ASSESS_SECTIONS[self.task]):
            raise ValueError(f"retrySections must be sections of the {self.task} task.")
        return self


class AssessResponse(BaseModel):
    content: str
    model: str
    # The prompt's version, for the tasks that have one; None for the rest.
    promptVersion: str | None = None
