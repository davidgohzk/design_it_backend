"""The rationale judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "links"
VERSION = "rationale-1"

PROMPT = (
    """You judge whether each supplied link in a design-document reasoning chain makes sense.

""" + EVIDENCE_RULES + """

Return one JSON object: {"links": [{"id": "link id", "verdict": "sound | weak | unsound", "reason": "short reason", "quote": "exact words from source or target"}]}.
Each link supplies its source and target text. A citation should support a requirement, a requirement should support a decision, a decision should explain its sketch, and a sketch should fit the final diagram. Return one entry per link. Quote exactly; use null when no quote supports a judgment.
"""
)
