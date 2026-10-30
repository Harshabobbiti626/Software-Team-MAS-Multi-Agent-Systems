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
    art_retrieved = bb.get_artifact("art-1")
    assert art_retrieved is not None
    assert art_retrieved.content == "# Test PRD v2"
    assert len(bb.get_by_type(ArtifactType.PRD)) == 1


def test_blackboard_target_workspace_sync(tmp_path):
    target_repo = tmp_path / "target_repo"
    (target_repo / "src").mkdir(parents=True)
    (target_repo / "src" / "components").mkdir(parents=True)
    (target_repo / "migrations").mkdir(parents=True)

    bb_repo = tmp_path / "bb_repo"
    bb_repo.mkdir()

    bb = ArtifactBlackboard(
        repo_path=str(bb_repo),
        git_enabled=False,
        target_workspace_dir=str(target_repo),
    )

    # 1. Python backend service -> target_repo/src/service.py
    bb.register_artifact(
        artifact_id="code-1",
        artifact_type=ArtifactType.CODE_PATCH,
        name="service.py",
        content="print('service')",
        created_by="BackendEngineer",
    )
    assert (target_repo / "src" / "service.py").exists()
    assert (target_repo / "src" / "service.py").read_text() == "print('service')"

    # 2. React UI component -> target_repo/src/components/ResourceView.tsx
    bb.register_artifact(
        artifact_id="code-2",
        artifact_type=ArtifactType.CODE_PATCH,
        name="ResourceView.tsx",
        content="export const View = () => null;",
        created_by="FrontendEngineer",
    )
    assert (target_repo / "src" / "components" / "ResourceView.tsx").exists()

    # 3. SQL migration -> target_repo/migrations/schema.sql
    bb.register_artifact(
        artifact_id="schema-1",
        artifact_type=ArtifactType.SCHEMA_SQL,
        name="schema.sql",
        content="CREATE TABLE users (id UUID);",
        created_by="DBA",
    )
    assert (target_repo / "migrations" / "schema.sql").exists()

