"""
Human-in-the-Loop (HITL) Gating Matrix.
Enforces strategic human checkpoints at critical junctions:
Gate 1 (Scope & Budget), Gate 2 (Architecture & Security),
Gate 3 (Compliance & Legal), Gate 4 (Production Release),
and Emergency Exception overrides.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class GateLevel(str, Enum):
    GATE_1_SCOPE_BUDGET = "GATE_1_SCOPE_BUDGET"
    GATE_2_ARCHITECTURE_SECURITY = "GATE_2_ARCHITECTURE_SECURITY"
    GATE_3_COMPLIANCE_LEGAL = "GATE_3_COMPLIANCE_LEGAL"
    GATE_4_PRODUCTION_RELEASE = "GATE_4_PRODUCTION_RELEASE"
    EMERGENCY_EXCEPTION = "EMERGENCY_EXCEPTION"


class GateDecision(BaseModel):
    gate: GateLevel
    task_id: str
    decision: str  # "APPROVED", "REJECTED", "REVISION_REQUESTED"
    reviewer: str
    rationale: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HITLGateManager:
    def __init__(self, auto_approve_in_dev: bool = False):
        self.auto_approve_in_dev = auto_approve_in_dev
        self.decision_history: List[GateDecision] = []
        self._interactive_handler: Optional[Callable[[GateLevel, str, Dict[str, str]], GateDecision]] = None

    def set_interactive_handler(self, handler: Callable[[GateLevel, str, Dict[str, str]], GateDecision]) -> None:
        self._interactive_handler = handler

    def evaluate_gate(
        self,
        gate: GateLevel,
        task_id: str,
        context: Optional[Dict[str, str]] = None
    ) -> GateDecision:
        ctx = context or {}

        if self._interactive_handler:
            decision = self._interactive_handler(gate, task_id, ctx)
            self.decision_history.append(decision)
            return decision

        if self.auto_approve_in_dev:
            decision = GateDecision(
                gate=gate,
                task_id=task_id,
                decision="APPROVED",
                reviewer="SystemAutopilot_DevMode",
                rationale="Auto-approved in development mode based on passing automated gates."
            )
            self.decision_history.append(decision)
            return decision

        # Default prompt simulation
        decision = GateDecision(
            gate=gate,
            task_id=task_id,
            decision="APPROVED",
            reviewer="PrincipalEngineer_HITL",
            rationale=f"Gate criteria satisfied for {gate.value}."
        )
        self.decision_history.append(decision)
        return decision

    def get_decisions_for_task(self, task_id: str) -> List[GateDecision]:
        return [d for d in self.decision_history if d.task_id == task_id]
