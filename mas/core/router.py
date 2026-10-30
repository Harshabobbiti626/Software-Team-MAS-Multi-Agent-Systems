"""
Intelligent Loopback & Dynamic Assignment Router.
Performs diagnostic attribution and routes scoped remediation tickets
to the exact responsible pod without blame or chaotic ping-ponging.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from mas.core.state import SubsystemClass, TestReport


class FailureCategory(str, Enum):
    SPECIFICATION_GAP = "SPECIFICATION_GAP"
    DESIGN_DRIFT = "DESIGN_DRIFT"
    CODE_LOGIC_FLAW = "CODE_LOGIC_FLAW"
    QA_DEFECT = "QA_DEFECT"
    INFRASTRUCTURE_FLAW = "INFRASTRUCTURE_FLAW"


class RemediationTicket(BaseModel):
    ticket_id: str
    task_id: str
    failure_category: FailureCategory
    target_pod: SubsystemClass
    assignee_role: str
    root_cause_summary: str
    reproduction_command: str
    affected_files: List[str] = Field(default_factory=list)
    suggested_action: str


class IntelligentRouter:
    """
    Analyzes test failures, compiler/linter errors, and runtime crashes to attribute responsibility.
    """

    def triage_failure(
        self,
        task_id: str,
        test_report: Optional[TestReport] = None,
        error_output: str = "",
        contract_spec: str = ""
    ) -> RemediationTicket:
        combined_error = (error_output + "\n" + (test_report.stderr if test_report else "") + "\n" + (test_report.stdout if test_report else "")).lower()

        # 1. Check for contract / API drift
        if "404" in combined_error or "schema mismatch" in combined_error or "field missing" in combined_error or "422" in combined_error:
            return RemediationTicket(
                ticket_id=f"REM-{task_id[:8]}-01",
                task_id=task_id,
                failure_category=FailureCategory.DESIGN_DRIFT,
                target_pod=SubsystemClass.BACKEND,
                assignee_role="BackendEngineerAgent",
                root_cause_summary="API response payload does not conform to agreed OpenAPI contract schema.",
                reproduction_command="pytest tests/integration/ -k test_contract_compliance",
                affected_files=["mas/agents/engineering/backend.py"],
                suggested_action="Synchronize endpoint serializers and Pydantic schemas with `api-spec.yaml`."
            )

        # 2. Check for database / migration locks
        if "deadlock" in combined_error or "lock timeout" in combined_error or "relation does not exist" in combined_error:
            return RemediationTicket(
                ticket_id=f"REM-{task_id[:8]}-02",
                task_id=task_id,
                failure_category=FailureCategory.CODE_LOGIC_FLAW,
                target_pod=SubsystemClass.DATA,
                assignee_role="DatabaseArchitectAgent",
                root_cause_summary="Database migration lock timeout or missing relation index.",
                reproduction_command="pytest tests/data/ -k test_migrations",
                affected_files=["artifacts/schema_sql/schema.sql"],
                suggested_action="Refactor DDL to use CREATE INDEX CONCURRENTLY and nullable column migrations."
            )

        # 3. Check for QA Defect (e.g. assertion explicitly contradicting PRD requirement)
        if "assertionerror: expected true == false" in combined_error and "test_" in combined_error:
            return RemediationTicket(
                ticket_id=f"REM-{task_id[:8]}-03",
                task_id=task_id,
                failure_category=FailureCategory.QA_DEFECT,
                target_pod=SubsystemClass.QUALITY,
                assignee_role="QASDETAgent",
                root_cause_summary="Test assertion appears out of sync with updated acceptance criteria.",
                reproduction_command="pytest tests/ -k test_failing_assertion",
                affected_files=["tests/"],
                suggested_action="Verify test assertion against latest PRD acceptance criteria in Artifact Blackboard."
            )

        # 4. Check for Specification Gap / Domain Ambiguity
        if "unspecified" in combined_error or "not defined in prd" in combined_error or "domain rule" in combined_error:
            return RemediationTicket(
                ticket_id=f"REM-{task_id[:8]}-04",
                task_id=task_id,
                failure_category=FailureCategory.SPECIFICATION_GAP,
                target_pod=SubsystemClass.BUSINESS,
                assignee_role="ProductManagerAgent",
                root_cause_summary="Ambiguity in business rule or acceptance criteria.",
                reproduction_command="mas verify --task-id " + task_id,
                affected_files=["artifacts/prd/PRD.md"],
                suggested_action="Clarify domain boundary and update user story acceptance criteria."
            )

        # 5. Default to Code Logic Flaw
        return RemediationTicket(
            ticket_id=f"REM-{task_id[:8]}-05",
            task_id=task_id,
            failure_category=FailureCategory.CODE_LOGIC_FLAW,
            target_pod=SubsystemClass.BACKEND,
            assignee_role="BackendEngineerAgent",
            root_cause_summary="Application logic exception, syntax error, or unhandled runtime failure.",
            reproduction_command="pytest tests/unit/ -v",
            affected_files=["src/"],
            suggested_action="Inspect stack trace, apply defensive bounds checks, and re-run unit test."
        )
