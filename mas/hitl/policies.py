"""
Escalation Policies and Risk Scoring for HITL Gating.
Calculates risk scores and triggers emergency escalations.
"""

from typing import Any, Dict


class EscalationPolicy:
    def __init__(self, high_risk_threshold: float = 0.75):
        self.high_risk_threshold = high_risk_threshold

    def calculate_risk_score(self, task_description: str, metadata: Dict[str, Any]) -> float:
        score = 0.1
        desc = task_description.lower()
        if "delete" in desc or "drop table" in desc or "truncate" in desc:
            score += 0.6
        if (
            "pci" in desc
            or "hipaa" in desc
            or "auth" in desc
            or "secret" in desc
            or "payment" in desc
        ):
            score += 0.4
        if "migration" in desc or "schema" in desc:
            score += 0.3
        return min(1.0, score)

    def should_escalate_to_human(self, failure_count: int, risk_score: float) -> bool:
        if failure_count >= 2:
            return True
        if risk_score >= self.high_risk_threshold:
            return True
        return False
