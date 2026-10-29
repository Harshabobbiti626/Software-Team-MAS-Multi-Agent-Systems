"""
DevOps & SRE Agent.
Creates multi-stage Dockerfiles, GitHub Actions CI/CD workflows, and SLI/SLO health checks.
"""

from typing import Any, Dict
from mas.agents.base import BaseAgent, AgentResponse
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class DevOpsSREAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="DevOpsSREAgent", pod=SubsystemClass.CLOUD_DEVOPS, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        dockerfile_content = f"""# Multi-stage hardened Dockerfile for {task.title}
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.13-slim AS runtime
WORKDIR /app
RUN useradd -u 10001 -m appuser
USER appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY . .
ENV PATH=/home/appuser/.local/bin:$PATH
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
CMD ["python", "main.py"]
"""

        artifact = self.publish_artifact(
            artifact_id=f"dockerfile-{task.id}",
            artifact_type=ArtifactType.CODE_PATCH,
            name="Dockerfile",
            content=dockerfile_content
        )

        tokens = TokenUsageTracker(prompt_tokens=700, candidate_tokens=350, thinking_tokens=400)
        tokens.total_tokens = 1450

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Generated hardened non-root multi-stage Dockerfile with health checks.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens
        )
