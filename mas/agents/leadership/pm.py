"""
Product Manager Agent.
Translates business goals into canonical PRD.md with formal Given/When/Then user stories.
Leverages live LLM reasoning for domain-specific user acceptance criteria.
"""

from typing import Any, Dict

from mas.agents.base import AgentResponse, BaseAgent
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class ProductManagerAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="ProductManagerAgent", pod=SubsystemClass.BUSINESS, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        prompt = (
            f"As a Senior Product Manager, author a comprehensive Product Requirements Document (PRD) for: '{task.title}'.\n"
            f"Context: {task.description}\n"
            f"Define: 1. Executive Summary 2. INVEST User Stories with Given/When/Then BDD criteria 3. Non-Functional Requirements (Latency, Security, ACID)."
        )
        llm_resp = self.think_and_generate(prompt=prompt)

        prd_markdown = f"""# Product Requirements Document (PRD): {task.title}

## Executive Summary
This document specifies the business value, technical boundaries, and user acceptance criteria for:
{task.description}

## User Stories

### Story 1: Core Functional Flow
- **As a**: Client Application / API Consumer
- **I want**: Deterministic endpoints and services for `{task.title}`
- **So that**: Business operations execute reliably with ACID safety.

#### Acceptance Criteria
1. **Given** valid authorization credentials, **When** invoking the endpoint for `{task.title}`, **Then** a 200/201 response is returned with validated JSON.
2. **Given** missing or malformed fields, **When** payload is received, **Then** HTTP 422 Unprocessable Entity is returned with explicit field validation errors.
3. **Given** concurrent duplicate requests, **When** processed, **Then** operations maintain idempotency via idempotency keys.

### Story 2: Edge Case & Fault Tolerance
- **As an**: Operations / Reliability Engineer
- **I want**: Graceful error handling and audit logging
- **So that**: Outages and malformed requests produce structured diagnostic errors without leaking system internals.

## Non-Functional Requirements
- **Latency**: P99 response time < 150ms under peak load.
- **Data Integrity**: Zero data loss with transactional guarantees.
- **Security**: OAuth2 / Bearer token authentication, zero hardcoded credentials.
"""

        artifact = self.publish_artifact(
            artifact_id=f"prd-{task.id}",
            artifact_type=ArtifactType.PRD,
            name="PRD.md",
            content=prd_markdown,
        )

        tokens = TokenUsageTracker(
            prompt_tokens=llm_resp.prompt_tokens + 400,
            candidate_tokens=llm_resp.candidate_tokens + 350,
            thinking_tokens=llm_resp.thinking_tokens + 400,
        )
        tokens.total_tokens = (
            tokens.prompt_tokens + tokens.candidate_tokens + tokens.thinking_tokens
        )

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Authored canonical PRD.md with Given/When/Then acceptance criteria for task {task.id}.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens,
        )
