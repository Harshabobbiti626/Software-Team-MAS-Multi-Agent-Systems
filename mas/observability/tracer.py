"""
OpenTelemetry-Style Distributed Tracer & Cost Tracker.
Records execution spans, token usage (including extended thinking tokens),
latency, and end-to-end provenance graphs.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TraceSpan(BaseModel):
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_span_id: Optional[str] = None
    task_id: str
    agent_name: str
    agent_role: str
    operation: str
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0.0
    status: str = "OK"  # "OK", "ERROR"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DistributedTracer:
    # Cost assumptions (e.g. per 1M tokens)
    PROMPT_COST_PER_MILLION = 1.25
    CANDIDATE_COST_PER_MILLION = 5.00
    THINKING_COST_PER_MILLION = 5.00

    def __init__(self):
        self._spans: List[TraceSpan] = []

    def start_span(
        self,
        task_id: str,
        agent_name: str,
        agent_role: str,
        operation: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TraceSpan:
        span = TraceSpan(
            task_id=task_id,
            agent_name=agent_name,
            agent_role=agent_role,
            operation=operation,
            parent_span_id=parent_span_id,
            attributes=attributes or {}
        )
        self._spans.append(span)
        return span

    def finish_span(
        self,
        span: TraceSpan,
        prompt_tokens: int = 0,
        candidate_tokens: int = 0,
        thinking_tokens: int = 0,
        duration_ms: float = 0.0,
        status: str = "OK"
    ) -> None:
        span.prompt_tokens = prompt_tokens
        span.candidate_tokens = candidate_tokens
        span.thinking_tokens = thinking_tokens
        span.total_tokens = prompt_tokens + candidate_tokens + thinking_tokens
        span.duration_ms = duration_ms
        span.status = status

    def get_spans_for_task(self, task_id: str) -> List[TraceSpan]:
        return [s for s in self._spans if s.task_id == task_id]

    def calculate_total_cost(self, task_id: Optional[str] = None) -> Dict[str, float]:
        spans = self._spans if task_id is None else self.get_spans_for_task(task_id)
        total_prompt = sum(s.prompt_tokens for s in spans)
        total_candidate = sum(s.candidate_tokens for s in spans)
        total_thinking = sum(s.thinking_tokens for s in spans)

        prompt_cost = (total_prompt / 1_000_000.0) * self.PROMPT_COST_PER_MILLION
        candidate_cost = (total_candidate / 1_000_000.0) * self.CANDIDATE_COST_PER_MILLION
        thinking_cost = (total_thinking / 1_000_000.0) * self.THINKING_COST_PER_MILLION

        return {
            "prompt_tokens": total_prompt,
            "candidate_tokens": total_candidate,
            "thinking_tokens": total_thinking,
            "total_tokens": total_prompt + total_candidate + total_thinking,
            "estimated_cost_usd": round(prompt_cost + candidate_cost + thinking_cost, 4)
        }

    def generate_provenance_header(
        self,
        commit_hash: str,
        task_id: str,
        api_endpoint: str,
        adr_id: str,
        story_id: str,
        business_goal_id: str
    ) -> Dict[str, str]:
        """
        Creates an immutable provenance chain:
        Commit -> Task -> API -> ADR -> Story -> Goal.
        """
        return {
            "Commit-Hash": commit_hash,
            "Task-ID": task_id,
            "API-Endpoint": api_endpoint,
            "ADR-Ref": adr_id,
            "PRD-Story": story_id,
            "Business-Objective": business_goal_id
        }
