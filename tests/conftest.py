import dataclasses
import os

# Set before importing the app: app.main builds a module-level app from the environment.
os.environ["SOCLAAS_API_KEY"] = "server-test-key"
os.environ["SOCLAAS_MODEL"] = "test-model"
os.environ["SOCLAAS_BASE_URL"] = "http://soclaas.test/v1"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.fakes import FakeClient, FakeState  # noqa: E402


@pytest.fixture
def fake() -> FakeState:
    return FakeState()


@pytest.fixture
def make_client(fake):
    def build(**overrides) -> TestClient:
        settings = dataclasses.replace(Settings.from_env(), **overrides)
        app = create_app(settings)
        app.state.llm_client = FakeClient(fake, settings.soclaas_api_key)
        return TestClient(app)

    return build


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
