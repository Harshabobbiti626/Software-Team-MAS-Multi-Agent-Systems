"""
Domain Subject Matter Expert (SME) Agent.
Validates requirements and system contracts against domain ontologies, compliance, and regulatory rules.
"""

import json
from typing import Any, Dict

from mas.agents.base import AgentResponse, BaseAgent
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker
from mas.tools.domain_verifier import DomainVerifier


class DomainSMEAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="DomainSMEAgent", pod=SubsystemClass.BUSINESS, **kwargs)
        self.verifier = DomainVerifier()

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        # Check existing PRD if present
        prd_artifact = self.blackboard.get_artifact(f"prd-{task.id}")
        prd_text = prd_artifact.content if prd_artifact else task.description

        val_result = self.verifier.verify_prd(prd_text)
        matrix = {
            "task_id": task.id,
            "domain_compliance": "PASSED" if val_result.is_valid else "FAILED",
            "checked_rules_count": val_result.checked_invariants_count,
            "violations": [v.model_dump() for v in val_result.violations],
            "regulatory_frameworks_audited": ["GDPR_DATA_MINIMIZATION", "PCI_DSS_SECRETS_MASKING"],
            "certified_by": self.role
        }

        artifact = self.publish_artifact(
            artifact_id=f"domain-validation-{task.id}",
            artifact_type=ArtifactType.DOMAIN_VALIDATION,
            name="DomainValidationMatrix.json",
            content=json.dumps(matrix, indent=2)
        )

        tokens = TokenUsageTracker(prompt_tokens=600, candidate_tokens=300, thinking_tokens=800)
        tokens.total_tokens = 1700

        status = "SUCCESS" if val_result.is_valid else "BLOCKED"
        return AgentResponse(
            agent_role=self.role,
            status=status,
            summary=f"Domain verification complete: {len(val_result.violations)} violations detected.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens
        )
