"""The match judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "matches"
VERSION = None

PROMPT = (
    """You decide whether a requirement in an engineer's design doc states a fact the client told them.

"""
    + EVIDENCE_RULES
    + """

Each pair gives a fact, the client's quote that surfaced it, a requirement, and the quote the requirement cites from the same client message.
Return one JSON object only, with this exact shape:
{
  "matches": [{"pairId": "pair id", "statesFact": true, "quote": "exact words from the requirement that state the fact", "reason": "one short sentence"}]
}

Rules:
- Return exactly one item for every pair, in the same order.
- statesFact is true only when the requirement's text states the substance of the fact, even in other words. A requirement that cites the same message for a different point is false.
- When statesFact is true, quote the requirement's own words that state it. Without an exact quote, return false."""
)
