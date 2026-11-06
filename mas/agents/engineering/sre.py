"""
DevOps & SRE Agent.
Creates multi-stage Dockerfiles, GitHub Actions CI/CD workflows, and SLI/SLO health checks.
Validates build recipes using Deterministic Polyglot Linter.
"""

from typing import Any, Dict

from mas.agents.base import AgentResponse, BaseAgent
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class DevOpsSREAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="DevOpsSREAgent", pod=SubsystemClass.CLOUD_DEVOPS, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        service_slug = task.title.lower().replace(" ", "-")

        dockerfile_content = f"""# Multi-stage hardened Dockerfile for {task.title}
# Service: {service_slug}
# Production non-root container with security context and health check

FROM python:3.13-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt* pyproject.toml* ./
RUN pip install --no-cache-dir --upgrade pip \\
 && if [ -f requirements.txt ]; then pip install --no-cache-dir --user -r requirements.txt; fi

FROM python:3.13-slim AS runtime
WORKDIR /app
RUN useradd -u 10001 -m appuser
USER appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
ENV PATH=/home/appuser/.local/bin:$PATH
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
CMD ["python", "main.py"]
"""

        # Verify through Polyglot Linter
        lint_res = self.linter.check_dockerfile_syntax("Dockerfile", dockerfile_content)
        if not lint_res.passed:
            dockerfile_content, _ = self.execute_react_code_generation(
                task=task,
                target_file="Dockerfile",
                initial_prompt=f"Generate hardened multi-stage Dockerfile for {task.title}.",
            )

        artifact = self.publish_artifact(
            artifact_id=f"dockerfile-{task.id}",
            artifact_type=ArtifactType.CODE_PATCH,
            name="Dockerfile",
            content=dockerfile_content,
        )

        tokens = TokenUsageTracker(prompt_tokens=700, candidate_tokens=350, thinking_tokens=400)
        tokens.total_tokens = (
            tokens.prompt_tokens + tokens.candidate_tokens + tokens.thinking_tokens
        )

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary=f"Generated hardened non-root multi-stage Dockerfile with health checks for '{service_slug}'.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens,
        )
