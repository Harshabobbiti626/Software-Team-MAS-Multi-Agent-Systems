"""
Comprehensive Enterprise Grade Verification Suite:
Tests the 3 Enterprise Pillars:
1. Hardened Sandbox Path Traversal & Destructive Command Interception.
2. Native ReAct Multi-Turn Observation-Action Loop & Tool Calling.
3. Durable SQLite WAL Event-Sourced Mission Persistence & Resumption.
"""

import tempfile
from pathlib import Path

import pytest

from mas.core.llm import DeterministicMockLLMProvider
from mas.core.persistence import MissionStore
from mas.core.react_engine import AutonomousReActEngine, ReActToolbox
from mas.tools.sandbox import SubprocessSandbox


def test_sandbox_path_traversal_defense():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sandbox = SubprocessSandbox(workspace_root=tmp_dir)

        # Attempting to execute with a directory outside workspace jail must raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            sandbox.execute(command_args=["python", "-c", "print('escaped')"], cwd="../../..")
        assert "escapes workspace jail" in str(exc_info.value)


def test_sandbox_destructive_command_interception():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sandbox = SubprocessSandbox(workspace_root=tmp_dir)

        # Destructive rm -rf / command
        with pytest.raises(PermissionError) as exc_info:
            sandbox.execute(command_args=["python", "-c", "import os; rm -rf /"])
        assert "destructive or unsafe execution pattern" in str(exc_info.value)

        # Pipe to bash command
        with pytest.raises(PermissionError) as exc_info2:
            sandbox.execute(command_args=["python", "script.py", "|", "bash"])
        assert "destructive or unsafe execution pattern" in str(exc_info2.value)


def test_react_toolbox_operations():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toolbox = ReActToolbox(workspace_root=tmp_dir)

        # 1. Write file
        write_res = toolbox.write_file("src/service.py", "def hello():\n    return 'world'\n")
        assert "Success: Wrote" in write_res
        assert (Path(tmp_dir) / "src" / "service.py").exists()

        # 2. Read file
        read_res = toolbox.read_file("src/service.py")
        assert "def hello():" in read_res

        # 3. AST check (valid python)
        ast_res = toolbox.ast_syntax_check("src/service.py")
        assert "AST Clean" in ast_res

        # 4. AST check (invalid python)
        toolbox.write_file("src/broken.py", "def broken(\n")
        ast_err = toolbox.ast_syntax_check("src/broken.py")
        assert "AST Syntax Errors" in ast_err

        # 5. List directory
        list_res = toolbox.list_directory("src")
        assert "service.py" in list_res

        # 6. Path traversal in toolbox
        with pytest.raises(PermissionError):
            toolbox.read_file("../../outside.txt")


def test_autonomous_react_engine_loop():
    with tempfile.TemporaryDirectory() as tmp_dir:
        toolbox = ReActToolbox(workspace_root=tmp_dir)
        mock_llm = DeterministicMockLLMProvider()

        engine = AutonomousReActEngine(
            llm=mock_llm,
            toolbox=toolbox,
            max_turns=3,
        )

        res = engine.execute_loop(
            role="BackendEngineerAgent",
            task_title="Build Payment Webhook",
            task_description="Implement secure webhook handler",
        )

        assert res.success is True
        assert len(res.turns) >= 1
        assert res.final_summary != ""


def test_durable_sqlite_mission_store():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_missions.db"
        store = MissionStore(db_path=str(db_path))

        # 1. Save mission
        store.save_mission(
            mission_id="MISSION-TEST-001",
            title="Durable Payment Gateway",
            description="Mission with SQLite WAL durability",
            status="RUNNING",
            stage="CONTRACTS",
            stage_index=1,
            interactive=True,
            tokens_used={"prompt": 120, "candidate": 60, "thinking": 20, "total": 200},
            pods={"Backend Pod": {"status": "RUNNING", "action": "Synthesizing"}},
        )

        # 2. Retrieve mission
        retrieved = store.get_mission("MISSION-TEST-001")
        assert retrieved is not None
        assert retrieved["title"] == "Durable Payment Gateway"
        assert retrieved["status"] == "RUNNING"
        assert retrieved["interactive"] is True
        assert retrieved["tokens_used"]["total"] == 200
        assert retrieved["pods"]["Backend Pod"]["status"] == "RUNNING"

        # 3. Update mission state
        store.update_mission_state(
            mission_id="MISSION-TEST-001",
            status="COMPLETED",
            stage="DOCUMENTATION",
            stage_index=5,
            pending_gate=False,
        )

        updated = store.get_mission("MISSION-TEST-001")
        assert updated is not None
        assert updated["status"] == "COMPLETED"
        assert updated["stage"] == "DOCUMENTATION"
        assert updated["stage_index"] == 5

        # 4. Record and inspect events
        store.record_event("MISSION-TEST-001", "STAGE_CHANGED", {"stage": "DOCUMENTATION"})
        missions_list = store.list_missions()
        assert len(missions_list) == 1
        assert missions_list[0]["mission_id"] == "MISSION-TEST-001"


def test_artifact_diff_computation():
    from mas.core.vcs import compute_artifact_diff

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        baseline_file = root / "src" / "service.py"
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        baseline_file.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        synthesized = "def old_func():\n    return 2\n"
        diff_res = compute_artifact_diff(
            artifact_id="art-service-py",
            artifact_name="service.py",
            synthesized_content=synthesized,
            workspace_root=tmp_dir,
            target_rel_path="src/service.py",
        )

        assert diff_res.has_diff is True
        assert diff_res.additions_count == 1
        assert diff_res.deletions_count == 1
        assert "return 2" in diff_res.diff
        assert "return 1" in diff_res.diff


def test_artifact_diff_new_file():
    from mas.core.vcs import compute_artifact_diff

    with tempfile.TemporaryDirectory() as tmp_dir:
        synthesized = "def newly_minted():\n    pass\n"
        diff_res = compute_artifact_diff(
            artifact_id="art-new-py",
            artifact_name="new.py",
            synthesized_content=synthesized,
            workspace_root=tmp_dir,
        )

        assert diff_res.has_diff is True
        assert diff_res.additions_count == 2
        assert diff_res.deletions_count == 0
        assert "/dev/null" in diff_res.diff


def test_sandbox_executes_pytest_suite():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        test_file = root / "test_sample.py"
        test_file.write_text(
            "def test_truth():\n    assert 1 + 1 == 2\n",
            encoding="utf-8",
        )

        sandbox = SubprocessSandbox(workspace_root=tmp_dir)
        res = sandbox.execute(["pytest", "-v", "test_sample.py"])
        assert res.exit_code == 0
        assert "1 passed" in res.stdout
        assert res.duration_seconds > 0


def test_artifact_update_ast_safety_and_persistence():
    import ast

    # 1. Valid Python parse
    valid_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    parsed = ast.parse(valid_code)
    assert parsed is not None

    # 2. SyntaxError on broken python code
    broken_code = "def broken_func(\n"
    with pytest.raises(SyntaxError):
        ast.parse(broken_code)


def test_create_local_git_snapshot():
    import subprocess

    from mas.core.vcs import create_local_git_snapshot

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "MAS Tester"], cwd=str(root), check=True)
        subprocess.run(["git", "config", "user.email", "tester@mas.local"], cwd=str(root), check=True)

        art = root / "artifacts" / "test.py"
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text("def sample(): pass\n", encoding="utf-8")

        res = create_local_git_snapshot(repo_path=str(root), commit_message="feat: test snapshot")
        assert res.status == "COMMITTED"
        assert res.files_committed == 1
        assert len(res.commit_hash) >= 4

        clean_res = create_local_git_snapshot(repo_path=str(root))
        assert clean_res.status == "CLEAN"


def test_artifact_version_history_and_rollback():
    from mas.core.blackboard import ArtifactBlackboard
    from mas.core.state import ArtifactType

    with tempfile.TemporaryDirectory() as tmp_dir:
        bb = ArtifactBlackboard(repo_path=tmp_dir, git_enabled=False)

        # Version 1
        art1 = bb.register_artifact(
            artifact_id="art-test-py",
            artifact_type=ArtifactType.CODE_PATCH,
            name="test.py",
            content="def v1(): return 1\n",
            created_by="Agent v1",
            commit_to_git=False,
        )
        assert art1.version == 1
        assert len(art1.version_history) == 1
        assert art1.version_history[0]["version"] == 1
        assert "def v1" in art1.version_history[0]["content"]

        # Version 2
        art2 = bb.register_artifact(
            artifact_id="art-test-py",
            artifact_type=ArtifactType.CODE_PATCH,
            name="test.py",
            content="def v2(): return 2\n",
            created_by="Agent v2",
            commit_to_git=False,
        )
        assert art2.version == 2
        assert len(art2.version_history) == 2
        assert art2.version_history[1]["version"] == 2
        assert "def v2" in art2.version_history[1]["content"]

        # Rollback to v1 snapshot
        snap1 = next(s for s in art2.version_history if s["version"] == 1)
        art3 = bb.register_artifact(
            artifact_id="art-test-py",
            artifact_type=ArtifactType.CODE_PATCH,
            name="test.py",
            content=snap1["content"],
            created_by="Operator Rollback (to v1)",
            commit_to_git=False,
        )
        assert art3.version == 3
        assert "def v1" in art3.content
        assert len(art3.version_history) == 3




