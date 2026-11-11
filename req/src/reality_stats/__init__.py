"""Untrusted statistical helpers for AI-eval measures (outside the v4 trusted base).

Wilson score interval, bootstrap CI (pinned seed), Cohen's kappa, multi-metric
tables. Outputs are ordinary TSV bytes; Reality v4 checks claims on those bytes.
Changing seed/confidence/thresholds requires a new adopted measure (params live
in the fragment / producer invocation that the measure pins by hash or constant).

This package never signs and never claims immutable history.
"""
from .intervals import bootstrap_ci_lower, cohens_kappa, wilson_lower

__all__ = ["wilson_lower", "bootstrap_ci_lower", "cohens_kappa"]
