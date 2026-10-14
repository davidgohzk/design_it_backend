"""The structured client (WP2): the persona replies as JSON, code checks each reply, and only an
approved reply is streamed to the browser."""

import logging
import time

from fastapi.responses import StreamingResponse

from .guard import ReplyCheck, allowed_facts, check_reply
from .llm import LLM, UpstreamSlots, complete_json, stream_reply
from .prompts import CASE_FACTS, structured_persona_prompt

logger = logging.getLogger("design_it.client")

GUARD_FALLBACK_REPLY = "I'm not sure, I'd have to check."

CHAT_PARAMS = {"temperature": 1, "top_p": 1, "max_tokens": 2000}


def reply_schema(case_id: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "disclosedFactIds": {
                "type": "array",
                "items": {"type": "string", "enum": [fact["id"] for fact in CASE_FACTS[case_id]]},
            },
        },
        "required": ["reply", "disclosedFactIds"],
        "additionalProperties": False,
    }


def read_reply(value: dict) -> tuple[str, list[str]]:
    reply = value.get("reply")
    ids = value.get("disclosedFactIds")
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError("The reply is empty.")
    if not isinstance(ids, list):
        ids = []
    return reply.strip(), [item for item in ids if isinstance(item, str)]


async def structured_reply(llm: LLM, slots: UpstreamSlots, case_id: str, history: list[dict]) -> dict:
    """Ask the persona, check the reply, regenerate once with the offending facts forbidden, and fall
    back to a safe reply if it still breaks the rules. Returns the reply, its fact ids and the guard log."""
    facts = CASE_FACTS[case_id]
    allowed = allowed_facts(facts, history)
    turns = [{"role": turn["role"], "content": turn["content"]} for turn in history]
    forbidden: tuple[str, ...] = ()
    attempts: list[dict] = []
    check = ReplyCheck()
    for _attempt in range(2):
        messages = [{"role": "system", "content": structured_persona_prompt(case_id, forbidden)}, *turns]
        value = await complete_json(llm, slots, messages, name="client_reply", schema=reply_schema(case_id), **CHAT_PARAMS)
        try:
            reply, declared = read_reply(value)
        except ValueError:
            reply, declared = "", []
        check = check_reply(facts, reply, declared, allowed) if reply else ReplyCheck()
        attempts.append({"declared": declared, "blocked": check.blocked, "leaks": check.leaks, "phantoms": check.phantoms})
        if reply and not check.blocked:
            return {
                "reply": reply,
                "disclosedFactIds": check.disclosed,
                "guard": {
                    "action": "regenerated" if len(attempts) > 1 else "ok",
                    "leaks": check.leaks,
                    "phantoms": check.phantoms,
                    "attempts": attempts,
                },
            }
        forbidden = tuple(sorted(set(forbidden) | set(check.blocked)))
    logger.info("guard_block case=%s blocked=%s", case_id, forbidden)
    return {
        "reply": GUARD_FALLBACK_REPLY,
        "disclosedFactIds": [],
        "guard": {"action": "guard_block", "leaks": check.leaks, "phantoms": check.phantoms, "attempts": attempts},
    }


async def structured_chat(llm: LLM, slots: UpstreamSlots, case_id: str, history: list[dict]) -> StreamingResponse:
    result = await structured_reply(llm, slots, case_id, history)
    done = {
        "model": llm.model,
        "disclosedFactIds": result["disclosedFactIds"],
        "guard": result["guard"],
        "serverTime": int(time.time() * 1000),
    }
    return stream_reply(result["reply"], done)
