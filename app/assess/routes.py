"""POST /api/assess — one step of the review.

This route deliberately does no validation of the model's answer: it returns the raw string, and the
browser parses it, verifies every quote by string match and discards what does not match. Keeping
the judging on the client is what makes an unverifiable claim impossible to show.
"""

import dataclasses
import json

from fastapi import APIRouter, Depends, Request

from ..llm import LLM, complete, get_llm
from ..ratelimit import rate_limited
from .prompts import ASSESS_PROMPT_VERSIONS, ASSESS_PROMPTS, assess_retry_prompt
from .schemas import AssessRequest, AssessResponse

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limited)])


@router.post("/assess", response_model=AssessResponse)
async def assess(body: AssessRequest, request: Request, llm: LLM = Depends(get_llm)) -> AssessResponse:
    """One step of the review. The browser verifies every quote in the reply by string match."""
    model = request.app.state.settings.soclaas_assess_model or llm.model
    llm = dataclasses.replace(llm, model=model)
    system_prompt = ASSESS_PROMPTS[body.task]
    if body.retrySections:
        system_prompt += assess_retry_prompt(body.retrySections)
    evidence = {"facts": [fact.model_dump(exclude_none=True) for fact in body.facts], **body.evidence}
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))},
    ]
    # The judge runs at temperature 0, so repeated runs differ only where the model is unsure.
    content = await complete(llm, request.app.state.upstream_slots, messages, temperature=0, max_tokens=8000)
    return AssessResponse(content=content, model=model, promptVersion=ASSESS_PROMPT_VERSIONS.get(body.task))
