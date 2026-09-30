import dataclasses
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .assess_prompts import ASSESS_PROMPT_VERSION, ASSESS_PROMPTS, assess_retry_prompt
from .llm import LLM, complete, get_llm, stream_completion
from .prompts import DIAGRAM_PROMPT_VERSION, DIAGRAM_SYSTEM_PROMPT, PERSONAS
from .ratelimit import rate_limited
from .schemas import AssessRequest, AssessResponse, ChatRequest, DiagramRequest

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


def diagram_messages(body: DiagramRequest) -> list[dict]:
    messages = [{"role": "system", "content": DIAGRAM_SYSTEM_PROMPT}]
    if body.context and body.context.strip():
        messages.append({
            "role": "user",
            "content": f"Nodes in the decision sketches (use these IDs for the same components):\n{body.context.strip()}",
        })
    if body.currentCode:
        messages.append({"role": "user", "content": f"Existing diagram:\n{body.currentCode}"})
    messages.append({"role": "user", "content": body.prompt})
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
        prompt_version=DIAGRAM_PROMPT_VERSION,
        temperature=0.2,
        top_p=1,
        max_tokens=4000,
    )


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
    content = await complete(llm, request.app.state.upstream_slots, messages, temperature=0.1, max_tokens=8000)
    return AssessResponse(content=content, model=model, promptVersion=ASSESS_PROMPT_VERSION)
