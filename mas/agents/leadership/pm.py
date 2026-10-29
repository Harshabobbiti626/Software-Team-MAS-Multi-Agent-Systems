"""
Product Manager Agent.
Translates business goals into canonical PRD.md with formal Given/When/Then user stories.
"""

from typing import Any, Dict
from mas.agents.base import BaseAgent, AgentResponse
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class ProductManagerAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="ProductManagerAgent", pod=SubsystemClass.BUSINESS, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        prd_markdown = f"""# Product Requirements Document (PRD): {task.title}

## Executive Summary
This document specifies the technical requirements and user acceptance criteria for:
{task.description}

## User Stories

### Story 1: Core Functional Flow
- **As a**: Client Application / API Consumer
- **I want**: Deterministic endpoints for `{task.title}`
- **So that**: Business operations execute reliably with ACID safety.

#### Acceptance Criteria
1. **Given** valid authorization credentials, **When** invoking the endpoint, **Then** a 200/201 response is returned with validated JSON.
2. **Given** missing or malformed fields, **When** payload is received, **Then** HTTP 422 Unprocessable Entity is returned with explicit field validation errors.
3. **Given** concurrent duplicate requests, **When** processed, **Then** operations maintain idempotency via idempotency keys.

## Non-Functional Requirements
- **Latency**: P99 response time < 150ms under peak load.
- **Data Integrity**: Zero data loss with transactional guarantees.
- **Security**: OAuth2 / Bearer token authentication, zero hardcoded credentials.
"""

        artifact = self.publish_artifact(
            artifact_id=f"prd-{task.id}",
            artifact_type=ArtifactType.PRD,
            name="PRD.md",
            content=prd_markdown
        )

        tokens = TokenUsageTracker(prompt_tokens=850, candidate_tokens=450, thinking_tokens=600)
        tokens.total_tokens = 1900

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Authored canonical PRD.md with Given/When/Then acceptance criteria for task {task.id}.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens
        )
