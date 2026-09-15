import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from .llm import LLM, complete, get_llm, stream_completion
from .prompts import CHAT_SYSTEM_PROMPT, MERMAID_SYSTEM_PROMPT, REVIEW_PROMPT
from .ratelimit import rate_limited
from .schemas import ChatRequest, DiagramRequest, ReviewRequest, ReviewResponse

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limited)])


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, llm: LLM = Depends(get_llm)) -> StreamingResponse:
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    messages += [turn.model_dump() for turn in body.messages]
    return await stream_completion(
        llm, request.app.state.upstream_slots, messages, temperature=1, top_p=1, max_tokens=8000
    )


def diagram_messages(body: DiagramRequest) -> list[dict]:
    messages = [{"role": "system", "content": MERMAID_SYSTEM_PROMPT}]
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
        llm, request.app.state.upstream_slots, diagram_messages(body), temperature=0.2, top_p=1, max_tokens=4000
    )


@router.post("/review", response_model=ReviewResponse)
async def review(body: ReviewRequest, request: Request, llm: LLM = Depends(get_llm)) -> ReviewResponse:
    # Compact separators match JSON.stringify, so the prompt is identical to the old browser call.
    evidence = json.dumps(body.model_dump(), ensure_ascii=False, separators=(",", ":"))
    messages = [
        {"role": "system", "content": REVIEW_PROMPT},
        {"role": "user", "content": evidence},
    ]
    content = await complete(llm, request.app.state.upstream_slots, messages, temperature=0.1, max_tokens=8000)
    return ReviewResponse(content=content)
