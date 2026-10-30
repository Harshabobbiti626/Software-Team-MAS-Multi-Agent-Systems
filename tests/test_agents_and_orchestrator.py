import pytest
from mas.core.orchestrator import MASOrchestrator
from mas.core.state import SubsystemClass, TaskPriority, TestReport
from mas.core.blackboard import ArtifactBlackboard
from mas.agents.leadership import BusinessSponsorAgent, ProductManagerAgent
from mas.agents.engineering import BackendEngineerAgent, DatabaseArchitectAgent, FrontendEngineerAgent
from mas.agents.governance_docs import QASDETAgent
from main import run_pipeline, generate_pr_command


def test_orchestrator_blast_radius():
    orch = MASOrchestrator()
    # Data only
    sub1 = orch.analyze_blast_radius("Optimize PostgreSQL database migration for user table")
    assert sub1 == SubsystemClass.DATA
    pods1 = orch.determine_active_pods(sub1)
    assert "DatabaseArchitectAgent" in pods1
    assert "FrontendEngineerAgent" not in pods1

    # Frontend only
    sub2 = orch.analyze_blast_radius("Update React UI button styles and accessibility CSS")
    assert sub2 == SubsystemClass.FRONTEND

    # Full system
    sub3 = orch.analyze_blast_radius("Build new enterprise order checkout system with microservices and UI")
    assert sub3 == SubsystemClass.FULL_SYSTEM


def test_individual_agent_execution(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    orch = MASOrchestrator(blackboard=bb)
    task = orch.create_task("T-1", "Resource Endpoint", "Build Resource API")

    be = BackendEngineerAgent(blackboard=bb)
    res = be.run(task)
    assert res.status == "SUCCESS"
    assert len(res.artifacts_produced) > 0


def test_concurrent_parallel_pods_execution(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    orch = MASOrchestrator(blackboard=bb)
    task = orch.create_task("T-CONCURRENT", "Order Checkout Service", "Build checkout APIs and UI")

    pod_agents = [
        DatabaseArchitectAgent(blackboard=bb),
        BackendEngineerAgent(blackboard=bb),
        FrontendEngineerAgent(blackboard=bb)
    ]

    results = orch.execute_parallel_pods(task, pod_agents, max_workers=3)
    assert len(results) == 3
    assert "DatabaseArchitectAgent" in results
    assert "BackendEngineerAgent" in results
    assert "FrontendEngineerAgent" in results
    assert results["BackendEngineerAgent"].status == "SUCCESS"


def test_remediation_loop(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    orch = MASOrchestrator(blackboard=bb)
    task = orch.create_task("T-REMED", "Payment Service", "Build payment processing")

    failing_report = TestReport(
        id="TR-FAIL",
        task_id=task.id,
        test_suite="integration",
        total_tests=2,
        passed=0,
        failed=2,
        stderr="ValidationError: field missing in schema response 422",
        passed_all=False
    )

    be = BackendEngineerAgent(blackboard=bb)
    qa = QASDETAgent(blackboard=bb)
    agent_roster = {"BackendEngineerAgent": be}

    # Should remediate and succeed
    remediated = orch.trigger_remediation_loop(task, failing_report, agent_roster, qa, max_remediation_attempts=2)
    assert remediated is True


def test_pr_command():
    exit_code = generate_pr_command(task_id="TASK-TEST")
    assert exit_code == 0


def test_full_pipeline_run():
    exit_code = run_pipeline("Integration Test Service", "Build resource service with API and storage")
    assert exit_code == 0
