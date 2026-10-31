"""The bano judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "items"
VERSION = "bano-1"

PROMPT = (
    """You review a transcript of an engineer interviewing a client, and say which of a listed set of interviewing mistakes the engineer made.

"""
    + EVIDENCE_RULES
    + """

The transcript is numbered. Each message says whether the engineer or the client wrote it. Judge only the engineer's messages; the client's are context.
Each item gives an id, the mistake in one line, a definition, an example of the mistake for this case and an example of a good question for this case.
Return one JSON object only, with this exact shape:
{
  "items": [{"id": "QF1", "observed": true, "evidence": [{"messageIndex": 3, "quote": "exact words from that engineer message"}], "reason": "at most 25 words"}]
}

Rules:
- Return exactly one entry per item in the evidence, in the same order, using its id.
- observed is true only when the mistake is really there in this transcript. When you are unsure, return false: an unreported mistake costs less than one the engineer didn't make.
- When observed is true, give at least one piece of evidence: the number of an engineer message and words copied from it exactly. An entry with no exact quote is discarded, so quote exactly or return observed false.
- When observed is false, return an empty evidence list.
- Judge each item on its own. The examples show what the item means for this case; they are not the only form the mistake can take.
- Never return a count, a score, a total or a rating. This is teaching feedback, not a mark."""
)
