import pytest
from mas.core.orchestrator import MASOrchestrator
from mas.core.state import SubsystemClass, TaskPriority
from mas.core.blackboard import ArtifactBlackboard
from mas.agents.leadership import BusinessSponsorAgent, ProductManagerAgent
from mas.agents.engineering import BackendEngineerAgent, DatabaseArchitectAgent
from main import run_pipeline


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


def test_full_pipeline_run():
    exit_code = run_pipeline("Integration Test Service", "Build resource service with API and storage")
    assert exit_code == 0
