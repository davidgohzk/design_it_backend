"""The fit judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "scenarios"
VERSION = None

PROMPT = (
    """You check whether an engineer's design handles a situation the client will face.

"""
    + EVIDENCE_RULES
    + """

Each scenario gives a Given / When / Then situation, the design questions a good answer must address (with notes on good answers), the decisions the engineer picked as handling it (their text), and the engineer's one-line answer.
Return one JSON object only, with this exact shape:
{
  "scenarios": [{"scenarioId": "sc.x", "verdict": "handled | partly | not_handled", "reason": "at most 25 words", "quotes": [{"source": "answer | doc", "text": "exact words"}]}]
}

Rules:
- Return exactly one entry per scenario, in the same order.
- handled = the picked decisions and the one-liner together address every listed design question; partly = some of them; not_handled = none.
- Quote the one-liner (source "answer") or a picked decision (source "doc") exactly. Quote exactly, or return no quotes."""
)
