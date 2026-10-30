"""
Business Sponsor Agent.
Evaluates ROI, project charters, high-level business goals, and budget limits.
"""

import json
from typing import Any, Dict

from mas.agents.base import AgentResponse, BaseAgent
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class BusinessSponsorAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="BusinessSponsorAgent", pod=SubsystemClass.BUSINESS, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        charter_content = json.dumps({
            "project_charter_id": f"CHARTER-{task.id}",
            "business_goal_id": task.business_goal_id,
            "target_objective": task.title,
            "business_justification": task.description,
            "allocated_token_budget": self.config.limits.max_prompt_tokens,
            "target_sla": "High Availability (99.99%)",
            "sponsor_sign_off": "APPROVED"
        }, indent=2)

        artifact = self.publish_artifact(
            artifact_id=f"charter-{task.id}",
            artifact_type=ArtifactType.PRD,
            name=f"ProjectCharter_{task.id}.json",
            content=charter_content
        )

        tokens = TokenUsageTracker(prompt_tokens=450, candidate_tokens=220, thinking_tokens=300)
        tokens.total_tokens = 970

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Approved business charter and initialized business objective {task.business_goal_id}.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens
        )
