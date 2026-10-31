"""The justify judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "items"
VERSION = None

PROMPT = (
    """You are a senior system-design reviewer. You judge, item by item, whether each step of an engineer's design doc follows from the one before it.

"""
    + EVIDENCE_RULES
    + """

The evidence lists items of three kinds:
- requirement: an R# with the quotes it cites from the chat or the brief. Does it say what its quotes say?
- decision: a D# with the text of the requirements it is "because" of, the alternative it rejected, its trade-off and its quality. Does "because" support the choice, and is the choice sized to the evidence?
- sketch: a D#'s Mermaid sketch with the decision's text. Does the sketch show the decision, and nothing extra?

Verdicts: sound = it follows; weak = it partly follows, overstates, or adds something unsupported; unsound = it does not follow, or the evidence argues against it.
The rubric anchors are worked examples of each verdict for this case; judge like them.

Return one JSON object only, with this exact shape:
{
  "items": [{"itemId": "R1", "verdict": "sound | weak | unsound", "reason": "at most 25 words", "quotes": [{"source": "doc | chat | brief", "text": "exact words"}]}]
}

Rules:
- Return exactly one entry per item in the evidence, in the same order, using its itemId.
- Every entry needs at least one quote that shows why: words from the item itself (source "doc"), or from what it cites (source "chat" or "brief"). Quote exactly, or return no quotes.
- Judge only what is written. Keep each reason to 25 words or fewer."""
)
