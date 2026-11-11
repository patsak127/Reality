"""Untrusted statistical helpers for AI-eval measures (outside the v4 trusted base).

Wilson score interval, bootstrap CI (pinned seed), seed-variance across N runs,
Cohen's kappa, multi-metric tables, LLM-judge model/prompt hash columns.
Outputs are ordinary TSV bytes; Reality v4 checks claims on those bytes.
Changing seed/confidence/thresholds/judge hashes requires a new adopted measure
(params live in the fragment / producer invocation that the measure pins).

This package never signs and never claims immutable history.
"""
from .intervals import (
    bootstrap_ci_lower,
    cohens_kappa,
    seed_variance_lower,
    wilson_lower,
)

__all__ = [
    "wilson_lower",
    "bootstrap_ci_lower",
    "seed_variance_lower",
    "cohens_kappa",
]
