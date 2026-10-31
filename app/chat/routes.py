"""POST /api/chat — the interview with the client.

Two modes. Unstructured streams the persona's reply straight through. Structured (what the browser
sends) asks for JSON, checks every disclosure in code, and streams only an approved reply.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..llm import LLM, get_llm, stream_completion
from ..ratelimit import rate_limited
from .client import structured_chat
from .prompts import PERSONAS
from .schemas import ChatRequest

router = APIRouter(prefix="/api", dependencies=[Depends(rate_limited)])


@router.post("/chat")
async def chat(body: ChatRequest, request: Request, llm: LLM = Depends(get_llm)) -> StreamingResponse:
    if body.structured:
        history = [turn.model_dump(exclude_none=True) for turn in body.messages]
        return await structured_chat(llm, request.app.state.upstream_slots, body.caseId, history)
    persona = PERSONAS[body.caseId]
    messages = [{"role": "system", "content": persona["prompt"]}]
    messages += [turn.model_dump(include={"role", "content"}) for turn in body.messages]
    return await stream_completion(
        llm,
        request.app.state.upstream_slots,
        messages,
        temperature=1,
        top_p=1,
        max_tokens=8000,
    )
