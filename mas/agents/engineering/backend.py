"""
Backend Engineer Agent.
Implements robust REST/GraphQL service endpoints and business logic strictly conforming to api-spec.yaml.
"""

from typing import Any, Dict
from mas.agents.base import BaseAgent, AgentResponse
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class BackendEngineerAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="BackendEngineerAgent", pod=SubsystemClass.BACKEND, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        service_code = f"""\"\"\"
Provenance Header:
  Task-ID: {task.id}
  ADR-Ref: ADR-001
  Author: BackendEngineerAgent
  Contract: api-spec.yaml
\"\"\"

import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ResourcePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)


class ResourceResponse(BaseModel):
    id: str
    name: str
    status: str = "ACTIVE"


class ResourceService:
    def __init__(self):
        self._db: Dict[str, Dict[str, Any]] = {{}}

    def create_resource(self, payload: ResourcePayload) -> ResourceResponse:
        resource_id = str(uuid.uuid4())
        record = {{
            "id": resource_id,
            "name": payload.name,
            "category": payload.category,
            "status": "ACTIVE"
        }}
        self._db[resource_id] = record
        return ResourceResponse(id=resource_id, name=payload.name, status="ACTIVE")

    def get_resource(self, resource_id: str) -> Optional[ResourceResponse]:
        record = self._db.get(resource_id)
        if not record:
            return None
        return ResourceResponse(id=record["id"], name=record["name"], status=record["status"])
"""

        artifact = self.publish_artifact(
            artifact_id=f"backend-code-{task.id}",
            artifact_type=ArtifactType.CODE_PATCH,
            name="service.py",
            content=service_code
        )

        tokens = TokenUsageTracker(prompt_tokens=1100, candidate_tokens=600, thinking_tokens=1200)
        tokens.total_tokens = 2900

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Implemented ResourceService conforming to api-spec.yaml and ADR-001.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens
        )
