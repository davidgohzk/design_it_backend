"""Each case's facts come from app/cases/<case>.facts.json. The frontend keeps an identical copy
in design_it_frontend/src/cases/<case>/ and checks its case definitions against it."""

import json
from pathlib import Path

import pytest

from app.cases import CASE_FACTS, CASES_DIR
from app.chat.prompts import PERSONAS

FRONTEND_CASES_DIR = Path(__file__).resolve().parents[2] / "design_it_frontend" / "src" / "cases"

CASE_IDS = ["community-room"]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_persona_facts_come_from_the_facts_file(case_id):
    data = json.loads((CASES_DIR / f"{case_id}.facts.json").read_text(encoding="utf-8"))
    assert data["caseId"] == case_id
    assert PERSONAS[case_id]["facts"] == tuple((fact["id"], fact["detail"]) for fact in data["facts"])


def test_every_case_with_a_persona_has_a_facts_file():
    assert sorted(PERSONAS) == sorted(CASE_FACTS) == sorted(CASE_IDS)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_on_probe_facts_have_a_parent_and_probe_cues(case_id):
    facts = CASE_FACTS[case_id]
    ids = [fact["id"] for fact in facts]
    for fact in facts:
        assert fact["keywords"] and fact["signaturePhrases"], fact["id"]
        if fact["disclosure"] == "on-probe":
            assert fact["parentFactId"] in ids
            assert fact["probeCues"]
        else:
            assert "parentFactId" not in fact and "probeCues" not in fact


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_facts_file_matches_the_frontend_copy(case_id):
    frontend = FRONTEND_CASES_DIR / case_id / "facts.json"
    if not frontend.exists():
        pytest.skip("design_it_frontend is not checked out next to this repo")
    backend = CASES_DIR / f"{case_id}.facts.json"
    # Compared as parsed JSON, so line-ending conversion on checkout doesn't matter.
    assert json.loads(backend.read_text(encoding="utf-8")) == json.loads(frontend.read_text(encoding="utf-8"))
