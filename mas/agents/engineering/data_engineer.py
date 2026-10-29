"""
Data Engineer Agent.
Builds ETL/ELT ingestion pipelines (dbt, Spark, Kafka) and streaming transformations.
"""

from typing import Any, Dict
from mas.agents.base import BaseAgent, AgentResponse
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class DataEngineerAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="DataEngineerAgent", pod=SubsystemClass.DATA, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        dbt_model_sql = f"""-- dbt ELT Transformation Model for {task.title}
{{{{ config(materialized='incremental', unique_key='id') }}}}

SELECT
    id,
    name,
    category,
    status,
    created_at,
    updated_at
FROM {{{{ source('raw_data', 'resources') }}}}
WHERE updated_at > (SELECT coalesce(max(updated_at), '1970-01-01') FROM {{{{ this }}}})
"""

        artifact = self.publish_artifact(
            artifact_id=f"dbt-model-{task.id}",
            artifact_type=ArtifactType.CODE_PATCH,
            name="resources_incremental.sql",
            content=dbt_model_sql
        )

        tokens = TokenUsageTracker(prompt_tokens=650, candidate_tokens=300, thinking_tokens=400)
        tokens.total_tokens = 1350

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Authored incremental dbt model resources_incremental.sql.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens
        )
