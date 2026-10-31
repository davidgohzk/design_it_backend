"""Case content: the hidden facts each persona may disclose, and who may ask for them.

The facts are data, not prose. Every case keeps them in <case>.facts.json, and the frontend holds an
identical copy that tests on both sides compare, so the two halves cannot drift.
"""

import json
from pathlib import Path
from typing import Literal

# Community Room is the only persona served by the API and powers /demo.
CaseId = Literal["community-room"]

# This module lives in the cases directory, so the JSON sits beside it.
CASES_DIR = Path(__file__).parent


def load_case_facts(case_id: str) -> tuple[dict, ...]:
    """A case's facts, in order: id, detail, disclosure, topic area, keywords, phrases, probe cues."""
    data = json.loads((CASES_DIR / f"{case_id}.facts.json").read_text(encoding="utf-8"))
    if data["caseId"] != case_id:
        raise ValueError(f"{case_id}.facts.json is for {data['caseId']}.")
    return tuple(data["facts"])


CASE_FACTS = {"community-room": load_case_facts("community-room")}


def case_fact_ids(case_id: str) -> list[str]:
    """The case's fact ids, in file order. /api/assess requires exactly these."""
    return [fact["id"] for fact in CASE_FACTS[case_id]]
