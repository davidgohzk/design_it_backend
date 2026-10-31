"""The assertion judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "facts"
VERSION = None

PROMPT = (
    """You check whether an engineer's design doc asserts facts about a client that the client never told them.

"""
    + EVIDENCE_RULES
    + """

Each item gives a fact and one design-doc item (a requirement or decision) that mentions a word from the fact's area.
Return one JSON object only, with this exact shape:
{
  "facts": [{"factId": "fact id", "docAssertion": {"quote": "exact words from the design-doc item"} or null}]
}

Rules:
- Return exactly one item per fact, in the same order.
- docAssertion: the design-doc item itself states this fact (not just a word from its area). Quote the item's words that state it. If you are unsure, return null: prefer missed over assumed."""
)
