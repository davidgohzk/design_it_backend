import json

import openai

from app import llm as llm_module
from app.client import GUARD_FALLBACK_REPLY
from tests.fakes import status_error
from tests.test_api import parse_sse
from tests.transcripts import COMMUNITY_ROOM_GOLDEN, as_history


def body(history: list[dict], **extra) -> dict:
    return {"caseId": "community-room", "messages": history, "structured": True, **extra}


def replies(*values: dict):
    """A responder that answers each completion with the next JSON value."""
    queue = [json.dumps(value) for value in values]

    def respond(_kwargs):
        return queue.pop(0)

    return respond


def streamed(response) -> tuple[str, dict]:
    events = parse_sse(response.text)
    text = "".join(data["delta"] for name, data in events if name == "message")
    assert events[-1][0] == "done"
    return text, events[-1][1]


def setup_function():
    llm_module._NO_JSON_SCHEMA.clear()


def test_structured_chat_streams_an_approved_reply_and_ends_with_the_fact_ids(client, fake):
    reply = COMMUNITY_ROOM_GOLDEN[8][1]
    fake.responder = replies({"reply": reply, "disclosedFactIds": ["cr.root-cause"]})

    response = client.post("/api/chat", json=body(as_history(COMMUNITY_ROOM_GOLDEN, 7)))

    assert response.status_code == 200
    text, done = streamed(response)
    assert text == reply
    assert done["disclosedFactIds"] == ["cr.root-cause"]
    assert done["guard"]["action"] == "ok"
    assert done["model"] == "test-model"
    assert isinstance(done["serverTime"], int)
    call = fake.calls[0]
    assert call["response_format"]["type"] == "json_schema"
    assert "cr.root-cause:" in call["messages"][0]["content"]
    assert call["temperature"] == 1


def test_a_blocked_fact_is_regenerated_with_that_fact_forbidden(client, fake):
    history = [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "What problems do you have?"}]
    fake.responder = replies(
        {"reply": "People write a sticky note and it gets lost.", "disclosedFactIds": ["cr.root-cause"]},
        {"reply": "Double bookings keep happening, and people go home upset.", "disclosedFactIds": ["cr.current"]},
    )

    text, done = streamed(client.post("/api/chat", json=body(history)))

    assert text == "Double bookings keep happening, and people go home upset."
    assert done["guard"]["action"] == "regenerated"
    assert done["disclosedFactIds"] == ["cr.current"]
    second_prompt = fake.calls[1]["messages"][0]["content"]
    assert "do not reveal" in second_prompt
    assert second_prompt.rstrip().endswith("some notes never reach the book")


def test_a_reply_that_still_breaks_the_rules_falls_back_and_logs_guard_block(client, fake):
    history = [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "What problems do you have?"}]
    leak = {"reply": "It's the sticky note problem.", "disclosedFactIds": []}
    fake.responder = replies(leak, leak)

    text, done = streamed(client.post("/api/chat", json=body(history)))

    assert text == GUARD_FALLBACK_REPLY
    assert done["guard"]["action"] == "guard_block"
    assert done["disclosedFactIds"] == []
    assert len(fake.calls) == 2


def test_phantom_ids_are_removed(client, fake):
    history = [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "Who works at the desk?"}]
    fake.responder = replies({"reply": "It's a busy place!", "disclosedFactIds": ["cr.staff"]})

    _text, done = streamed(client.post("/api/chat", json=body(history)))

    assert done["disclosedFactIds"] == []
    assert done["guard"]["phantoms"] == ["cr.staff"]


def test_falls_back_to_json_mode_when_the_provider_rejects_json_schema(client, fake):
    history = [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "Who works at the desk?"}]
    good = json.dumps({"reply": "Two of us, on alternating shifts.", "disclosedFactIds": ["cr.staff"]})

    def respond(kwargs):
        if kwargs["response_format"]["type"] == "json_schema":
            return status_error(openai.BadRequestError, 400)
        return f"```json\n{good}\n```"

    fake.responder = respond

    text, done = streamed(client.post("/api/chat", json=body(history)))

    assert text == "Two of us, on alternating shifts."
    assert done["disclosedFactIds"] == ["cr.staff"]
    assert [call["response_format"]["type"] for call in fake.calls] == ["json_schema", "json_object"]
    # The fallback is remembered for this model.
    client.post("/api/chat", json=body(history))
    assert fake.calls[-1]["response_format"]["type"] == "json_object"


def test_invalid_json_is_asked_for_once_more_then_reported(client, fake):
    history = [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "Hello"}]
    fake.responder = lambda _kwargs: "not json"

    response = client.post("/api/chat", json=body(history))

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_json"
    assert len(fake.calls) == 2


def test_earlier_fact_ids_from_the_browser_count_as_disclosed(client, fake):
    history = [
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Who works at the desk?"},
        {"role": "assistant", "content": "Two of us.", "disclosedFactIds": ["cr.staff"]},
        {"role": "user", "content": "Tell me more."},
    ]
    fake.responder = replies({"reply": "Like I said, alternating shifts.", "disclosedFactIds": ["cr.staff"]})

    _text, done = streamed(client.post("/api/chat", json=body(history)))

    assert done["disclosedFactIds"] == ["cr.staff"]
    # The ids are not sent on to the model.
    assert all(set(turn) == {"role", "content"} for turn in fake.calls[0]["messages"][1:])


def test_structured_defaults_to_false_and_keeps_the_text_stream(client, fake):
    history = [{"role": "assistant", "content": "Hi"}, {"role": "user", "content": "Hello"}]

    response = client.post("/api/chat", json={"caseId": "community-room", "messages": history})

    assert parse_sse(response.text)[-1] == ("done", {"model": "test-model"})
    assert fake.calls[0]["stream"] is True
