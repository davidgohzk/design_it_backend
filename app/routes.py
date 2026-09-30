import dataclasses
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .assess_prompts import ASSESS_PROMPT_VERSION, ASSESS_PROMPTS, assess_retry_prompt
from .llm import LLM, complete, get_llm, stream_completion
from .prompts import (
    FINAL_PROMPT_VERSION,
    FINAL_SYSTEM_PROMPT,
    MERMAID_PROMPT_VERSION,
    MERMAID_SYSTEM_PROMPT,
    PERSONAS,
    REVIEW_PROMPT,
    SKETCH_PROMPT_VERSION,
    SKETCH_SYSTEM_PROMPT,
    review_retry_prompt,
)
from .ratelimit import rate_limited
from .schemas import AssessRequest, AssessResponse, ChatRequest, DiagramRequest, ReviewRequest, ReviewResponse

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limited)])


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, llm: LLM = Depends(get_llm)) -> StreamingResponse:
    persona = PERSONAS[body.caseId]
    messages = [{"role": "system", "content": persona["prompt"]}]
    messages += [turn.model_dump() for turn in body.messages]
    return await stream_completion(
        llm,
        request.app.state.upstream_slots,
        messages,
        prompt_version=persona["promptVersion"],
        temperature=1,
        top_p=1,
        max_tokens=8000,
    )


# mode None is the original free-form prompt (the frontend no longer sends it); "sketch" and "final" are the design doc's.
DIAGRAM_PROMPTS = {
    None: (MERMAID_SYSTEM_PROMPT, MERMAID_PROMPT_VERSION),
    "sketch": (SKETCH_SYSTEM_PROMPT, SKETCH_PROMPT_VERSION),
    "final": (FINAL_SYSTEM_PROMPT, FINAL_PROMPT_VERSION),
}


def diagram_messages(body: DiagramRequest) -> list[dict]:
    system_prompt, _version = DIAGRAM_PROMPTS[body.mode]
    messages = [{"role": "system", "content": system_prompt}]
    if body.mode == "sketch":
        used = (body.context or "").strip() or "(none yet)"
        messages.append({"role": "user", "content": f"Nodes already used in other sketches:\n{used}"})
    elif body.mode == "final" and body.context and body.context.strip():
        messages.append({
            "role": "user",
            "content": f"Nodes in the decision sketches (use these IDs for the same components):\n{body.context.strip()}",
        })
    if body.currentCode:
        label = "Current sketch" if body.mode == "sketch" else "Existing diagram"
        messages.append({"role": "user", "content": f"{label}:\n{body.currentCode}"})
    prompt = f"Decision:\n{body.prompt}" if body.mode == "sketch" else body.prompt
    messages.append({"role": "user", "content": prompt})
    if body.priorAttempt:
        messages.append({"role": "assistant", "content": body.priorAttempt.code})
        messages.append({
            "role": "user",
            "content": f"That diagram failed to parse with this error:\n{body.priorAttempt.error}\n\nReturn a corrected Mermaid diagram only.",
        })
    return messages


@router.post("/diagram")
async def diagram(body: DiagramRequest, request: Request, llm: LLM = Depends(get_llm)) -> StreamingResponse:
    return await stream_completion(
        llm,
        request.app.state.upstream_slots,
        diagram_messages(body),
        prompt_version=DIAGRAM_PROMPTS[body.mode][1],
        temperature=0.2,
        top_p=1,
        max_tokens=4000,
    )


@router.post("/review", response_model=ReviewResponse)
async def review(body: ReviewRequest, request: Request, llm: LLM = Depends(get_llm)) -> ReviewResponse:
    # retrySections becomes instructions, not evidence; acceptedClaims is evidence only on a partial retry.
    exclude = {"retrySections"} if body.acceptedClaims is not None else {"retrySections", "acceptedClaims"}
    # Compact separators match JSON.stringify, so the prompt is identical to the old browser call.
    evidence = json.dumps(body.model_dump(exclude=exclude), ensure_ascii=False, separators=(",", ":"))
    system_prompt = REVIEW_PROMPT
    if body.retrySections:
        system_prompt += review_retry_prompt(body.retrySections, has_accepted_claims=body.acceptedClaims is not None)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": evidence},
    ]
    content = await complete(llm, request.app.state.upstream_slots, messages, temperature=0.1, max_tokens=8000)
    return ReviewResponse(content=content)


@router.post("/assess", response_model=AssessResponse)
async def assess(body: AssessRequest, request: Request, llm: LLM = Depends(get_llm)) -> AssessResponse:
    """One step of the /simple review. The browser verifies every quote in the reply by string match."""
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
    content = await complete(llm, request.app.state.upstream_slots, messages, temperature=0.1, max_tokens=8000)
    return AssessResponse(content=content, model=model, promptVersion=ASSESS_PROMPT_VERSION)
