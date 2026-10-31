"""The judge prompt registry, assembled from the per-task modules.

Each task owns its prompt, its section key and its version in one file, so the three registries
below cannot drift from the prompts they describe: they are derived, not repeated.
"""

from . import (
    assertion,
    bano,
    fit,
    iso,
    justify,
    match,
    rationale,
    scenario_adequacy,
    suggest,
    turns,
)
from .rules import EVIDENCE_RULES, assess_retry_prompt

# Order is the order a review issues them, which is also the order they are documented in.
_MODULES = {
    "match": match,
    "assertion": assertion,
    "justify": justify,
    "fit": fit,
    "suggest": suggest,
    "bano": bano,
    "turns": turns,
    "scenario_adequacy": scenario_adequacy,
    "iso": iso,
    "rationale": rationale,
}

ASSESS_PROMPTS = {task: module.PROMPT for task, module in _MODULES.items()}
ASSESS_SECTIONS = {task: (module.SECTION,) for task, module in _MODULES.items()}

# The version of a judge prompt, reported on the response and stored on the result, so a stored
# review says which prompt produced it. Only the tasks in here are versioned; the others came before
# versioning existed and are left alone.
ASSESS_PROMPT_VERSIONS = {
    task: module.VERSION for task, module in _MODULES.items() if module.VERSION is not None
}

BANO_PROMPT_VERSION = bano.VERSION

__all__ = [
    "ASSESS_PROMPTS",
    "ASSESS_SECTIONS",
    "ASSESS_PROMPT_VERSIONS",
    "BANO_PROMPT_VERSION",
    "EVIDENCE_RULES",
    "assess_retry_prompt",
]
