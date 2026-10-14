"""The cue guard and signature scan for the structured client (WP2).

Pure functions only. The persona says which facts its reply states; code decides whether the
engineer's latest message was allowed to unlock each one, and checks the reply text itself.
"""

import re
from dataclasses import dataclass, field


def normalise(text: str) -> str:
    """Lowercase, with curly quotes made straight, so phrases match however they were typed."""
    return text.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def contains_term(text: str, term: str) -> bool:
    """True when `term` appears in `text` as whole words (case-insensitive)."""
    pattern = r"(?<![a-z0-9])" + re.escape(normalise(term).strip()) + r"(?![a-z0-9])"
    return re.search(pattern, normalise(text)) is not None


def contains_phrase(text: str, phrase: str) -> bool:
    """True when `phrase` appears anywhere in `text` (case-insensitive substring)."""
    return normalise(phrase) in normalise(text)


def stated_facts(facts: tuple[dict, ...], text: str) -> list[str]:
    """Ids of the facts whose signature phrases appear in `text`, in case order."""
    return [fact["id"] for fact in facts if any(contains_phrase(text, p) for p in fact["signaturePhrases"])]


def disclosed_before(facts: tuple[dict, ...], history: list[dict]) -> set[str]:
    """Facts the client has already given: given facts, ids it declared, and facts its replies stated."""
    known = {fact["id"] for fact in facts}
    disclosed = {fact["id"] for fact in facts if fact["disclosure"] == "given"}
    for turn in history:
        if turn["role"] != "assistant":
            continue
        disclosed |= known & set(turn.get("disclosedFactIds") or [])
        disclosed |= set(stated_facts(facts, turn["content"]))
    return disclosed


def is_allowed(fact: dict, question: str, earlier: set[str]) -> bool:
    """May the client state this fact in reply to `question`, given the facts it gave before?"""
    if fact["id"] in earlier or fact["disclosure"] == "given":
        # Repeating a fact the engineer already has is not a new disclosure.
        return True
    if fact["disclosure"] == "on-ask":
        return any(contains_term(question, term) for term in [*fact["keywords"], *fact["cues"]])
    if fact["disclosure"] == "on-probe":
        parent = fact.get("parentFactId")
        return parent in earlier and any(contains_term(question, cue) for cue in fact.get("probeCues", []))
    return False


def allowed_facts(facts: tuple[dict, ...], history: list[dict]) -> set[str]:
    """The facts the client may state in reply to the last message of `history` (the engineer's)."""
    question = history[-1]["content"]
    earlier = disclosed_before(facts, history[:-1])
    return {fact["id"] for fact in facts if is_allowed(fact, question, earlier)}


@dataclass
class ReplyCheck:
    """What the guard found in one reply."""

    # Declared and backed by a signature phrase, plus allowed facts the reply stated without declaring.
    disclosed: list[str] = field(default_factory=list)
    # Declared or stated, but the engineer's message didn't unlock them.
    blocked: list[str] = field(default_factory=list)
    # Stated (a signature phrase is in the reply) but not declared.
    leaks: list[str] = field(default_factory=list)
    # Declared, but no signature phrase is in the reply.
    phantoms: list[str] = field(default_factory=list)


def check_reply(facts: tuple[dict, ...], reply: str, declared: list[str], allowed: set[str]) -> ReplyCheck:
    known = [fact["id"] for fact in facts]
    declared_set = set(declared) & set(known)
    stated = set(stated_facts(facts, reply))
    check = ReplyCheck()
    for fact_id in known:
        is_declared, is_stated, ok = fact_id in declared_set, fact_id in stated, fact_id in allowed
        if is_stated and not is_declared:
            check.leaks.append(fact_id)
        if (is_declared or is_stated) and not ok:
            # Blocked whatever the wording: a declared fact may be paraphrased past the phrase list.
            check.blocked.append(fact_id)
        elif is_declared and not is_stated:
            check.phantoms.append(fact_id)
        elif is_stated:
            check.disclosed.append(fact_id)
    return check
