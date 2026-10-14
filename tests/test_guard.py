import pytest

from app.guard import allowed_facts, check_reply, contains_term, disclosed_before
from app.prompts import CASE_FACTS
from tests.transcripts import (
    BRIGHTPATH_DISCLOSURES,
    BRIGHTPATH_GOLDEN,
    COMMUNITY_ROOM_DISCLOSURES,
    COMMUNITY_ROOM_GOLDEN,
    as_history,
)

CR = CASE_FACTS["community-room"]
OPENING = {"role": "assistant", "content": COMMUNITY_ROOM_GOLDEN[0][1]}


def ask(question: str, earlier: list[dict] | None = None) -> set[str]:
    return allowed_facts(CR, [OPENING, *(earlier or []), {"role": "user", "content": question}])


def test_contains_term_matches_whole_words_only():
    assert contains_term("How many ROOMS do you have?", "rooms")
    assert not contains_term("How many bedrooms?", "rooms")
    assert contains_term("Who usually makes the bookings?", "makes the bookings")
    assert contains_term("Why?", "why")


@pytest.mark.parametrize(
    "case_id, transcript, expected",
    [
        ("community-room", COMMUNITY_ROOM_GOLDEN, COMMUNITY_ROOM_DISCLOSURES),
        ("brightpath", BRIGHTPATH_GOLDEN, BRIGHTPATH_DISCLOSURES),
    ],
)
def test_golden_transcript_gives_the_expected_disclosures(case_id, transcript, expected):
    facts = CASE_FACTS[case_id]
    for index, fact_ids in expected.items():
        history = as_history(transcript, index - 1)
        reply = transcript[index][1]
        check = check_reply(facts, reply, fact_ids, allowed_facts(facts, history))
        assert check.blocked == [], (index, check)
        assert check.disclosed == fact_ids, (index, check)
        assert check.phantoms == [] and check.leaks == [], (index, check)


def test_a_general_question_does_not_unlock_the_root_cause():
    assert "cr.root-cause" not in ask("What problems do you have?")


def test_why_unlocks_the_root_cause_once_the_parent_is_known():
    # cr.current is given, so its parent rule holds from the start.
    assert "cr.root-cause" in ask("Why do you think the double bookings happen?")
    assert "cr.root-cause" in ask("How are phone bookings recorded?")


def test_on_ask_facts_need_a_keyword():
    assert "cr.staff" in ask("Who works at the desk?")
    assert "cr.staff" not in ask("What would you like from a new system?")


def test_a_fact_already_given_can_be_repeated():
    earlier = [
        {"role": "user", "content": "Who works at the desk?"},
        {"role": "assistant", "content": "Two of us on alternating shifts.", "disclosedFactIds": ["cr.staff"]},
    ]
    assert "cr.staff" in ask("Anything else?", earlier)
    assert "cr.staff" in disclosed_before(CR, earlier)


def test_a_forced_leak_is_caught_and_blocked():
    # The reply states the sticky notes without declaring them, after a question that doesn't unlock them.
    allowed = ask("What problems do you have?")
    check = check_reply(CR, "Double bookings, mostly. Someone writes a sticky note and it gets lost.", ["cr.current"], allowed)
    assert check.leaks == ["cr.root-cause"]
    assert check.blocked == ["cr.root-cause"]


def test_a_leak_of_an_allowed_fact_is_logged_and_counted():
    allowed = ask("How many rooms do you have?")
    check = check_reply(CR, "We have the activity hall and two others.", [], allowed)
    assert check.leaks == ["cr.scale"]
    assert check.disclosed == ["cr.scale"]
    assert check.blocked == []


def test_a_forced_phantom_is_removed():
    allowed = ask("Who works at the desk?")
    check = check_reply(CR, "It's a busy place, honestly.", ["cr.staff"], allowed)
    assert check.phantoms == ["cr.staff"]
    assert check.disclosed == []


def test_a_declared_fact_that_is_not_allowed_is_blocked_even_when_paraphrased():
    allowed = ask("What problems do you have?")
    check = check_reply(CR, "Some phone bookings get scribbled down and lost.", ["cr.root-cause"], allowed)
    assert check.blocked == ["cr.root-cause"]
