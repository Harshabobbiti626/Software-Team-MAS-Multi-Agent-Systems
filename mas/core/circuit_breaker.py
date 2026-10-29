"""
Circuit Breaker & Anti-Infinite-Loop Governor.
Enforces hard budgets, turn limits, thinking token caps, and 3-strike failure traps.
"""

from typing import Dict, List, Optional
from mas.core.config import LimitSettings


class CircuitBreakerTrippedException(Exception):
    """Raised when hard resource ceilings or loop detection thresholds are violated."""
    pass


class CircuitBreaker:
    def __init__(self, limits: Optional[LimitSettings] = None):
        self.limits = limits or LimitSettings()
        self.total_turns: int = 0
        self.agent_turns: Dict[str, int] = {}
        self.consecutive_failures: int = 0
        self.failure_history: List[str] = []
        self.prompt_tokens: int = 0
        self.candidate_tokens: int = 0
        self.thinking_tokens: int = 0
        self.tripped: bool = False
        self.trip_reason: Optional[str] = None

    def record_turn(self, agent_role: str) -> None:
        """Records an agent step and verifies turn limits."""
        if self.tripped:
            raise CircuitBreakerTrippedException(f"Circuit breaker already tripped: {self.trip_reason}")

        self.total_turns += 1
        self.agent_turns[agent_role] = self.agent_turns.get(agent_role, 0) + 1

        if self.total_turns > self.limits.max_total_turns_per_task:
            self._trip(f"Exceeded max total task turns ({self.total_turns} > {self.limits.max_total_turns_per_task})")

        if self.agent_turns[agent_role] > self.limits.max_turns_per_agent:
            self._trip(f"Agent '{agent_role}' exceeded max turns ({self.agent_turns[agent_role]} > {self.limits.max_turns_per_agent})")

    def record_tokens(self, prompt: int = 0, candidate: int = 0, thinking: int = 0) -> None:
        """Accumulates token consumption and checks hard ceilings."""
        self.prompt_tokens += prompt
        self.candidate_tokens += candidate
        self.thinking_tokens += thinking

        total_tokens = self.prompt_tokens + self.candidate_tokens + self.thinking_tokens

        if self.limits.circuit_breaker_enabled:
            if self.prompt_tokens > self.limits.max_prompt_tokens:
                self._trip(f"Prompt token cap exceeded: {self.prompt_tokens} > {self.limits.max_prompt_tokens}")
            if self.candidate_tokens > self.limits.max_candidate_tokens:
                self._trip(f"Candidate token cap exceeded: {self.candidate_tokens} > {self.limits.max_candidate_tokens}")
            if self.thinking_tokens > self.limits.max_thinking_tokens:
                self._trip(f"Thinking token cap exceeded: {self.thinking_tokens} > {self.limits.max_thinking_tokens}")

    def record_failure(self, failure_signature: str) -> None:
        """Tracks consecutive failures and traps repetitive error loops."""
        self.consecutive_failures += 1
        self.failure_history.append(failure_signature)

        # 3-strike rule
        if self.consecutive_failures >= self.limits.max_consecutive_failures:
            self._trip(f"Tripped 3-strike failure trap: {self.consecutive_failures} consecutive failures. Last error: {failure_signature}")

        # Repetitive loop trap (same exact error repeated twice consecutively)
        if len(self.failure_history) >= 2 and self.failure_history[-1] == self.failure_history[-2]:
            self._trip(f"Repetitive loop detected: identical failure repeated '{failure_signature[:120]}'")

    def record_success(self) -> None:
        """Resets consecutive failure count after a successful verification or task step."""
        self.consecutive_failures = 0

    def _trip(self, reason: str) -> None:
        self.tripped = True
        self.trip_reason = reason
        raise CircuitBreakerTrippedException(reason)

    def is_tripped(self) -> bool:
        return self.tripped

    def get_trip_reason(self) -> Optional[str]:
        return self.trip_reason

    def reset(self) -> None:
        self.total_turns = 0
        self.agent_turns.clear()
        self.consecutive_failures = 0
        self.failure_history.clear()
        self.prompt_tokens = 0
        self.candidate_tokens = 0
        self.thinking_tokens = 0
        self.tripped = False
        self.trip_reason = None
