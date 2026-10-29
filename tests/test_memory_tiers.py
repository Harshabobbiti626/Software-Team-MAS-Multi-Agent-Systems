import pytest
from mas.memory.working import WorkingMemory
from mas.memory.episodic import EpisodicMemory
from mas.memory.semantic import SemanticMemory
from mas.memory.procedural import ProceduralMemory


def test_working_memory_compaction():
    mem = WorkingMemory(window_size=4, compaction_threshold=1000)
    for i in range(6):
        mem.add_entry(role="Dev", content=f"Step {i}: executed tool action.")

    assert len(mem.entries) <= 4
    assert mem.compacted_summary is not None
    assert "Step 0" in mem.compacted_summary


def test_episodic_memory(tmp_path):
    db_file = tmp_path / "test_episodic.db"
    mem = EpisodicMemory(db_path=str(db_file))

    event_id = mem.record_event(
        session_id="sess-1",
        task_id="task-1",
        agent_role="BackendAgent",
        event_type="TEST_RUN",
        payload={"result": "PASS"}
    )
    assert event_id > 0

    events = mem.get_events_for_task("task-1")
    assert len(events) == 1
    assert events[0]["payload"]["result"] == "PASS"


def test_semantic_memory():
    mem = SemanticMemory()
    mem.add_document(
        doc_id="DOC-1",
        category="coding_guidelines",
        title="REST API Guidelines",
        content="Always use standard HTTP verbs and return json responses.",
        tags=["api", "rest"]
    )
    results = mem.query("HTTP verbs API", category="coding_guidelines")
    assert len(results) > 0
    assert results[0].doc_id == "DOC-1"


def test_procedural_memory():
    mem = ProceduralMemory()

    def add(a: int, b: int) -> int:
        return a + b

    mem.register_tool(
        name="calculator_add",
        description="Adds two integers",
        handler=add,
        roles_allowed=["BackendAgent"]
    )

    result = mem.execute_tool("calculator_add", caller_role="BackendAgent", a=3, b=7)
    assert result == 10

    with pytest.raises(PermissionError):
        mem.execute_tool("calculator_add", caller_role="FrontendAgent", a=1, b=1)
