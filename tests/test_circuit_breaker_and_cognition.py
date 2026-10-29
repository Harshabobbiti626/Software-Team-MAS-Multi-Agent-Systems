import pytest
from mas.core.circuit_breaker import CircuitBreaker, CircuitBreakerTrippedException
from mas.core.config import LimitSettings
from mas.core.cognition import CognitiveEngine


def test_circuit_breaker_turns():
    limits = LimitSettings(max_turns_per_agent=2, max_total_turns_per_task=5)
    cb = CircuitBreaker(limits)

    cb.record_turn("BackendAgent")
    cb.record_turn("BackendAgent")
    assert cb.total_turns == 2

    # Exceeding turns trips breaker
    with pytest.raises(CircuitBreakerTrippedException):
        cb.record_turn("BackendAgent")
    assert cb.is_tripped()


def test_circuit_breaker_failure_trap():
    limits = LimitSettings(max_consecutive_failures=3)
    cb = CircuitBreaker(limits)

    cb.record_failure("error 1")
    cb.record_failure("error 2")
    assert cb.consecutive_failures == 2

    with pytest.raises(CircuitBreakerTrippedException):
        cb.record_failure("error 3")
    assert cb.is_tripped()


def test_cognitive_engine_pre_mortem():
    engine = CognitiveEngine(thinking_budget=4096)
    analysis = engine.perform_pre_mortem(
        decision_summary="Database schema update",
        subsystem="Database",
        proposed_change="ALTER TABLE users ADD COLUMN phone VARCHAR(20);"
    )
    assert len(analysis.timeout_or_lock_risks) > 0
    assert analysis.pass_pre_mortem is True


def test_cognitive_engine_trade_off():
    engine = CognitiveEngine()
    eval_result = engine.evaluate_trade_off(
        topic="Caching Layer",
        option_a="Redis Distributed Cache",
        option_b="In-Memory Local Dict",
        reversibility="two-way"
    )
    assert eval_result.recommended_option == "Redis Distributed Cache"
    assert eval_result.reversibility == "two-way"
