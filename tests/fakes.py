from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import httpx


class FakeStream:
    def __init__(self, parts: list[str], error: Exception | None) -> None:
        self.parts = parts
        self.error = error
        self.closed = False

    async def _iterate(self):
        for part in self.parts:
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=part))])
        if self.error:
            raise self.error

    def __aiter__(self):
        return self._iterate()

    async def close(self) -> None:
        self.closed = True


@dataclass
class FakeState:
    chunks: list[str] = field(default_factory=lambda: ["Hello", " there"])
    content: str | None = '{"coverage": []}'
    error_before: Exception | None = None
    error_mid: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)
    streams: list[FakeStream] = field(default_factory=list)


class FakeCompletions:
    def __init__(self, client: "FakeClient") -> None:
        self._client = client

    async def create(self, **kwargs):
        state = self._client.state
        state.calls.append({"api_key": self._client.api_key, **kwargs})
        if state.error_before:
            raise state.error_before
        if kwargs.get("stream"):
            stream = FakeStream(state.chunks, state.error_mid)
            state.streams.append(stream)
            return stream
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=state.content))])


class FakeClient:
    """Stands in for AsyncOpenAI: records each call and the API key it was made with."""

    def __init__(self, state: FakeState, api_key: str | None) -> None:
        self.state = state
        self.api_key = api_key
        self.chat = SimpleNamespace(completions=FakeCompletions(self))


def status_error(cls, status: int, headers: dict[str, str] | None = None) -> Exception:
    request = httpx.Request("POST", "http://soclaas.test/v1/chat/completions")
    response = httpx.Response(status, request=request, headers=headers)
    return cls("upstream said no", response=response, body=None)
