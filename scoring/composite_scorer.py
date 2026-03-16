from __future__ import annotations

from scoring.quality_scorer import QualityScorer
from scoring.security_scorer import SecurityScorer


def build_default_scorers() -> list:
    return [QualityScorer(), SecurityScorer()]
