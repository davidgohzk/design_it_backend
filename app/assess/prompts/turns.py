"""The turns judge task.

SECTION is the one top-level key the reply must carry; VERSION is reported on the response
and stored on the review, so a stored review says which prompt produced it. Changing PROMPT
means bumping VERSION in the same edit.
"""

from .rules import EVIDENCE_RULES

SECTION = "turns"
VERSION = "turns-1"

PROMPT = (
    """You are an expert evaluator of a requirements-elicitation interview. Classify each interviewer action using its full preceding conversation.

"""
    + EVIDENCE_RULES
    + """

initialRequirements is the brief and transcript is the whole conversation, each message with its messageIndex and role ("user" is the interviewer, "assistant" is the client). For each turn, latestUtterance is the interviewer action at that messageIndex, its preceding conversation is the transcript up to that messageIndex, and remainingRequirements lists implicit requirements the client had not yet disclosed.
Action definitions: clarify asks for clarification of information mentioned earlier; probe explores new or more detailed requirements; finish concludes the conversation.
Determine whether each question targets any still-hidden listed requirements. Clarification questions can target them too. Use only requirement IDs in that turn's remainingRequirements.
Return one JSON object only:
{"turns": [{"messageIndex": 1, "action_type": "clarify | probe | finish", "is_relevant_to_implicit_requirements": true, "relevant_implicit_requirement_ids": ["fact.id"], "reasoning": "brief explanation"}]}
Return one entry per turn in order. Give every targeted ID, or an empty list. Set relevance true exactly when the list is nonempty. Never claim that the question succeeded; the client reply determines that separately.
"""
)
