"""
Automated Diagnostic Autopsy Engine (Root Cause Analysis - RCA).
Generates blameless post-mortem autopsies when tasks fail or test gates reject a release.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from mas.core.router import FailureCategory, IntelligentRouter, RemediationTicket
from mas.core.state import TestReport


class AutopsyReport(BaseModel):
    autopsy_id: str
    task_id: str
    failure_category: FailureCategory
    responsible_pod: str
    root_cause_analysis: str
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    remediation_ticket: RemediationTicket
    preventative_countermeasures: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiagnosticAutopsyEngine:
    def __init__(self, router: Optional[IntelligentRouter] = None):
        self.router = router or IntelligentRouter()

    def conduct_autopsy(
        self,
        task_id: str,
        test_report: Optional[TestReport] = None,
        error_logs: str = "",
        timeline_events: Optional[List[Dict[str, Any]]] = None
    ) -> AutopsyReport:
        ticket = self.router.triage_failure(
            task_id=task_id,
            test_report=test_report,
            error_output=error_logs
        )

        countermeasures = [
            f"Update {ticket.assignee_role} system prompt with strict validation bounds.",
            "Add automated pre-commit lint gate before code review handoff.",
            "Include regression test case in permanent test harness."
        ]

        return AutopsyReport(
            autopsy_id=f"AUTOPSY-{task_id[:8]}",
            task_id=task_id,
            failure_category=ticket.failure_category,
            responsible_pod=ticket.target_pod.value,
            root_cause_analysis=ticket.root_cause_summary,
            timeline_events=timeline_events or [],
            remediation_ticket=ticket,
            preventative_countermeasures=countermeasures
        )
