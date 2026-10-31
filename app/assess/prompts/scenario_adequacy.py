"""The scenario_adequacy judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "scenarios"
VERSION = "scenario-adequacy-1"

PROMPT = (
    """You evaluate each scenario against the engineer's selected decision, diagram components, and written explanation.

""" + EVIDENCE_RULES + """

Return one JSON object: {"scenarios": [{"scenarioId": "id", "decision": "sound | weak | unsound", "diagram": "sound | weak | unsound", "justification": "sound | weak | unsound", "reasons": {"decision": "short reason", "diagram": "short reason", "justification": "short reason"}, "quotes": [{"source": "answer | doc", "text": "exact words"}]}]}.
Judge only the selected path. A sound decision addresses the situation; sound diagram linkage uses selected final boxes that actually express the selected decision; a sound justification explains how that path handles the outcome. A weak result is partial, an unsound result is unsupported. Quote the supplied answer or design document exactly; without a supporting quote, return an empty quotes list.
"""
)
