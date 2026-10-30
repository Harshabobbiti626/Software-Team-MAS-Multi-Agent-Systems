from mas.core.blackboard import ArtifactBlackboard
from mas.core.state import (
    ADR,
    PRD,
    ADRStatus,
    ArtifactType,
    SubsystemClass,
    Task,
    TaskPriority,
    TaskStatus,
    UserStory,
)


def test_task_schema():
    task = Task(
        id="TASK-100",
        title="Implement Auth Service",
        description="Build OAuth2 token validation service",
        assigned_pod=SubsystemClass.BACKEND,
        priority=TaskPriority.HIGH,
    )
    assert task.id == "TASK-100"
    assert task.status == TaskStatus.PENDING
    assert task.assigned_pod == SubsystemClass.BACKEND


def test_prd_and_adr_schema():
    story = UserStory(
        id="STORY-1",
        as_a="User",
        i_want="Login",
        so_that="Access account",
        acceptance_criteria=["Given credentials When login Then succeed"],
    )
    prd = PRD(
        id="PRD-1",
        title="Auth PRD",
        business_goal_id="GOAL-1",
        executive_summary="Summary",
        user_stories=[story],
    )
    assert len(prd.user_stories) == 1
    assert prd.user_stories[0].id == "STORY-1"

    adr = ADR(
        id="ADR-001",
        title="Use JWT",
        context="Need stateless auth",
        decision="Use RS256 JWT tokens",
    )
    assert adr.status == ADRStatus.ACCEPTED
    assert adr.reversibility == "two-way"


def test_artifact_blackboard(tmp_path):
    bb = ArtifactBlackboard(repo_path=str(tmp_path), git_enabled=False)
    art1 = bb.register_artifact(
        artifact_id="art-1",
        artifact_type=ArtifactType.PRD,
        name="PRD.md",
        content="# Test PRD",
        created_by="ProductManager",
    )
    assert art1.version == 1
    assert (tmp_path / "artifacts" / "prd" / "PRD.md").exists()

    # Update artifact
    art2 = bb.register_artifact(
        artifact_id="art-1",
        artifact_type=ArtifactType.PRD,
        name="PRD.md",
        content="# Test PRD v2",
        created_by="ProductManager",
    )
    assert art2.version == 2
    assert bb.get_artifact("art-1").content == "# Test PRD v2"
    assert len(bb.get_by_type(ArtifactType.PRD)) == 1
