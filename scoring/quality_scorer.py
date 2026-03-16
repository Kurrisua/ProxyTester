from __future__ import annotations

from core.context.check_context import CheckContext
from core.interfaces.checker_base import BaseScorer
from core.models.results import ScoreResult


class QualityScorer(BaseScorer):
    name = "quality_scorer"

    def score(self, context: CheckContext) -> None:
        proxy = context.proxy
        total = proxy.success_count + proxy.fail_count
        success_rate = proxy.success_count / total if total else 0
        success_score = success_rate * 40
        speed_score = 0 if proxy.response_time is None else max(0, 30 - (proxy.response_time / 5000) * 30)
        business_score = (proxy.business_score / 3) * 30
        total_score = min(100, max(0, int(success_score + speed_score + business_score)))
        proxy.quality_score = total_score
        context.add_score_result(
            ScoreResult(
                scorer_name=self.name,
                score=total_score,
                breakdown={
                    "success_rate": round(success_rate, 4),
                    "response_time": proxy.response_time,
                    "business_score": proxy.business_score,
                },
            )
        )
