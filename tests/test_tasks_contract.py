"""app/assess/tasks.json is the /api/assess contract, and this pins both sides to it.

Adding a judge task means touching a prompt module, the AssessTask literal and the frontend. Nothing
in either repo could catch a half-done change before this file: the backend would accept a task the
browser never sends, or reject one it does.
"""

import json
import typing
from pathlib import Path

from app.assess.prompts import ASSESS_PROMPT_VERSIONS, ASSESS_PROMPTS, ASSESS_SECTIONS
from app.assess.schemas import AssessTask

CONTRACT = Path(__file__).resolve().parents[1] / "app" / "assess" / "tasks.json"
FRONTEND_CONTRACT = (
    Path(__file__).resolve().parents[2] / "design_it_frontend" / "src" / "review" / "judge" / "tasks.json"
)

TASKS = json.loads(CONTRACT.read_text(encoding="utf-8"))["tasks"]


def test_the_contract_lists_every_prompt_in_issue_order():
    assert [entry["task"] for entry in TASKS] == list(ASSESS_PROMPTS)


def test_every_task_declares_its_section():
    assert {entry["task"]: (entry["section"],) for entry in TASKS} == ASSESS_SECTIONS


def test_every_task_declares_its_prompt_version():
    versioned = {entry["task"]: entry["promptVersion"] for entry in TASKS if entry["promptVersion"]}
    assert versioned == ASSESS_PROMPT_VERSIONS


def test_the_request_schema_accepts_exactly_the_contract_tasks():
    assert sorted(typing.get_args(AssessTask)) == sorted(entry["task"] for entry in TASKS)


def test_the_frontend_copy_is_identical():
    if not FRONTEND_CONTRACT.exists():
        import pytest

        pytest.skip("design_it_frontend is not checked out next to this repo")
    # Compared as parsed JSON, so line-ending conversion on checkout doesn't matter.
    assert json.loads(FRONTEND_CONTRACT.read_text(encoding="utf-8")) == json.loads(
        CONTRACT.read_text(encoding="utf-8")
    )
