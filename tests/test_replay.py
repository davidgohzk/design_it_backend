"""Offline checks for the persona replay suite. The suite itself calls the model and is run on demand
with `python -m tests.replay.runner`."""

import asyncio
import json
from pathlib import Path

import pytest

from app.llm import LLM, UpstreamSlots
from app.prompts import CASE_FACTS
from tests.fakes import FakeClient, FakeState
from tests.replay.runner import OPENING, SCRIPTS_DIR, load_scripts, play, summarise

FRONTEND_CASES_DIR = Path(__file__).resolve().parents[2] / "design_it_frontend" / "src" / "cases"


@pytest.mark.parametrize("case_id", sorted(CASE_FACTS))
def test_scripts_name_real_facts(case_id):
    ids = {fact["id"] for fact in CASE_FACTS[case_id]}
    scripts = load_scripts(case_id)
    assert 20 <= len(scripts) <= 30
    for script in scripts:
        assert set(script["mustDisclose"]) | set(script["mustNotDisclose"]) <= ids


@pytest.mark.parametrize("case_id", sorted(CASE_FACTS))
def test_scripts_match_the_frontend_copy(case_id):
    frontend = FRONTEND_CASES_DIR / case_id / "replay.json"
    if not frontend.exists():
        pytest.skip("design_it_frontend is not checked out next to this repo")
    backend = SCRIPTS_DIR / f"{case_id}.replay.json"
    assert json.loads(backend.read_text(encoding="utf-8")) == json.loads(frontend.read_text(encoding="utf-8"))


def test_openings_match_the_frontend_cases():
    for case_id, opening in OPENING.items():
        source = FRONTEND_CASES_DIR / case_id / "index.ts"
        if not source.exists():
            pytest.skip("design_it_frontend is not checked out next to this repo")
        assert opening in source.read_text(encoding="utf-8")


def test_play_collects_disclosures_and_misses():
    state = FakeState()
    replies = iter([
        {"reply": "Two of us, on alternating shifts.", "disclosedFactIds": ["cr.staff"]},
        {"reply": "It's a sticky note problem.", "disclosedFactIds": ["cr.root-cause"]},
    ])
    state.responder = lambda _kwargs: json.dumps(next(replies))
    llm = LLM(FakeClient(state, "key"), "fake-model")
    script = {
        "id": "s",
        "messages": ["Who works at the desk?", "Why do the double bookings happen?"],
        "mustDisclose": ["cr.staff", "cr.root-cause"],
        "mustNotDisclose": ["cr.scale"],
    }

    run = asyncio.run(play(llm, UpstreamSlots(2), "community-room", script))

    assert run["disclosed"] == ["cr.root-cause", "cr.staff"]
    assert run["falsePositives"] == [] and run["falseNegatives"] == []
    # The second turn sends the first turn's fact ids back, so the parent rule can see them.
    assert len(run["turns"]) == 2


def test_summarise_gives_per_fact_rates_and_failing_facts():
    def item(must, must_not, fp, fn):
        script = {"id": "x", "messages": ["q"], "mustDisclose": must, "mustNotDisclose": must_not}
        turn = {"guard": {"action": "ok"}}
        return {"script": script, "run": {"falsePositives": fp, "falseNegatives": fn, "turns": [turn]}}

    results = [
        item(["cr.staff"], ["cr.root-cause"], [], []),
        item(["cr.staff"], ["cr.root-cause"], ["cr.root-cause"], ["cr.staff"]),
        item(["cr.staff"], ["cr.root-cause"], [], []),
        item(["cr.staff"], ["cr.root-cause"], [], []),
    ]

    summary = summarise("community-room", results)

    assert summary["perFact"]["cr.root-cause"]["falsePositiveRate"] == 0.25
    assert summary["perFact"]["cr.staff"]["falseNegativeRate"] == 0.25
    assert summary["falsePositiveRate"] == 0.25
    assert summary["meetsTargets"] is False
    assert summary["failingFacts"] == ["cr.root-cause", "cr.staff"]
    assert summary["guardActions"]["ok"] == 4
