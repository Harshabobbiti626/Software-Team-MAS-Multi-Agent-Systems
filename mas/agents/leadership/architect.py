"""
System Architect Agent.
Authors Architectural Decision Records (ADRs), evaluates non-functional trade-offs,
and executes pre-mortem failure mode reflections.
"""

from typing import Any, Dict
from mas.agents.base import BaseAgent, AgentResponse
from mas.core.state import ADR, ADRStatus, ArtifactType, SubsystemClass, Task, TokenUsageTracker


class SystemArchitectAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="SystemArchitectAgent", pod=SubsystemClass.ARCHITECTURE, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        # Extended thinking pre-mortem
        pre_mortem = self.cognition.perform_pre_mortem(
            decision_summary=f"Architecture design for {task.title}",
            subsystem="SystemArchitecture",
            proposed_change=task.description
        )

        trade_off = self.cognition.evaluate_trade_off(
            topic="Inter-Service Communication & Data Flow",
            option_a="Contract-first OpenAPI + Git-backed Artifact Ledger",
            option_b="Unstructured runtime JSON messaging",
            reversibility="two-way"
        )

        adr_content = f"""# ADR-001: Architecture & Interface Strategy for {task.title}

## Context
{task.description}

## Decision
We enforce a Contract-First architecture using typed Pydantic models and an OpenAPI v3 contract.
Data operations utilize transactional guarantees with backward-compatible schema evolutions.

## Consequences
- **Positive**: Strict contract boundaries enable parallel execution across Frontend, Backend, Data, and Cloud pods.
- **Positive**: Eliminates integration lockouts and runtime type drift.
- **Trade-offs**: Requires upfront schema drafting and contract compilation before pod code generation.

## Reversibility
- **Door Classification**: {trade_off.reversibility.upper()}
- **Recommendation**: {trade_off.recommended_option}

## Pre-Mortem Mitigations
{chr(10).join(f"- {m}" for m in pre_mortem.mitigations)}
"""

        artifact = self.publish_artifact(
            artifact_id=f"adr-001-{task.id}",
            artifact_type=ArtifactType.ADR,
            name="ADR-001.md",
            content=adr_content
        )

        tokens = TokenUsageTracker(prompt_tokens=1200, candidate_tokens=650, thinking_tokens=1500)
        tokens.total_tokens = 3350

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Authored ADR-001 for {task.title} with formal pre-mortem analysis.",
            artifacts_produced=[artifact.id],
            pre_mortem=pre_mortem,
            tokens_used=tokens
        )
