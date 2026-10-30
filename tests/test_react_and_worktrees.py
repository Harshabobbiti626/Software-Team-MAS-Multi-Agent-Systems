"""
Comprehensive Test Suite for ReAct Multi-Turn Self-Healing,
Git Worktree Parallel Pod Isolation, and Mission Control Console.
"""

from mas.agents.engineering import (
    BackendEngineerAgent,
    DatabaseArchitectAgent,
    FrontendEngineerAgent,
)
from mas.agents.governance_docs import QASDETAgent
from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.config import LimitSettings
from mas.core.orchestrator import MASOrchestrator
from mas.core.state import ArtifactType, SubsystemClass, Task
from mas.core.vcs import GitWorktreeManager
from mas.hitl.mission_control import MissionControlConsole


def test_react_code_generation_ast_verification(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    be = BackendEngineerAgent(blackboard=bb)
    task = Task(
        id="TASK-REACT-1",
        title="Payment Service Implementation",
        description="Build secure payment processing API",
        assigned_pod=SubsystemClass.BACKEND,
    )

    code, is_valid = be.execute_react_code_generation(
        task=task,
        target_file="payment.py",
        initial_prompt="Generate Python payment service with Pydantic models.",
    )
    assert is_valid is True
    assert len(code) > 0


def test_worktree_manager_merge(tmp_path):
    repo_dir = tmp_path / "main_repo"
    repo_dir.mkdir()
    mgr = GitWorktreeManager(repo_path=str(repo_dir))

    # Simulate pod worktree directory
    pod_dir = tmp_path / "pod_worktree"
    artifacts_dir = pod_dir / "artifacts" / "code_patch"
    artifacts_dir.mkdir(parents=True)
    sample_file = artifacts_dir / "schema.sql"
    sample_file.write_text("CREATE TABLE users (id SERIAL PRIMARY KEY);", encoding="utf-8")

    merged = mgr.merge_pod_worktrees([pod_dir], target_dir=repo_dir)
    assert len(merged) == 1
    assert "artifacts/code_patch/schema.sql" in merged[0]
    assert (repo_dir / "artifacts" / "code_patch" / "schema.sql").exists()


def test_parallel_pods_with_worktree_isolation(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    orch = MASOrchestrator(blackboard=bb)
    task = orch.create_task("T-ISOLATED", "Order Checkout Service", "Build checkout APIs and UI")

    pod_agents = [
        DatabaseArchitectAgent(blackboard=bb),
        BackendEngineerAgent(blackboard=bb),
        FrontendEngineerAgent(blackboard=bb),
    ]

    results = orch.execute_parallel_pods(task, pod_agents, max_workers=3, isolate_worktrees=True)
    assert len(results) == 3
    assert "BackendEngineerAgent" in results
    assert results["BackendEngineerAgent"].status == "SUCCESS"


def test_qa_sdet_real_test_execution(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    qa = QASDETAgent(blackboard=bb)
    task = Task(
        id="TASK-QA-1",
        title="Auth Microservice",
        description="User authentication and token generation",
        assigned_pod=SubsystemClass.QUALITY,
    )

    resp = qa.run(task)
    assert resp.status == "SUCCESS"
    assert resp.test_report is not None
    assert resp.test_report.passed_all is True
    assert resp.test_report.total_tests >= 2


def test_mission_control_console(tmp_path):
    console = MissionControlConsole(use_color=False)
    task = Task(
        id="TASK-UI-1",
        title="Billing Engine",
        description="Stripe billing engine",
        assigned_pod=SubsystemClass.BACKEND,
    )
    cb = CircuitBreaker(LimitSettings())
    cb.record_turn("BackendEngineerAgent")
    cb.record_tokens(prompt=150, candidate=75, thinking=200)

    banner_text = console.banner(task, cb)
    assert "TASK-UI-1" in banner_text
    assert "Billing Engine" in banner_text
    assert "Turns: 1" in banner_text

    matrix_text = console.render_pod_matrix(["BackendEngineerAgent"])
    assert "Backend & AI Pod" in matrix_text

    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    bb.register_artifact("art-t1", ArtifactType.PRD, "PRD.md", "# Billing PRD", "PM")
    ledger_text = console.render_artifact_ledger(bb)
    assert "art-t1" in ledger_text
    assert "PRD.md" in ledger_text or "PRD" in ledger_text
