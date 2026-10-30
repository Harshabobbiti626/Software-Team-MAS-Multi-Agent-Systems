from mas.core.state import SubsystemClass, Task, TestReport
from mas.core.vcs import GitWorktreeManager, PullRequestGenerator
from mas.memory.code_graph import CodeKnowledgeGraph, SymbolKind
from mas.observability.otlp import OTLPTraceExporter
from mas.observability.tracer import TraceSpan


def test_code_knowledge_graph_indexing(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    sample_file = pkg_dir / "models.py"
    sample_file.write_text(
        """
import uuid

class BaseEntity:
    pass

class Order(BaseEntity):
    \"\"\"Order entity representing a customer purchase.\"\"\"
    def __init__(self, order_id: str):
        self.order_id = order_id

    def calculate_tax(self, rate: float) -> float:
        return rate * 10.0

def process_order(order: Order):
    order.calculate_tax(0.05)
""",
        encoding="utf-8",
    )

    graph = CodeKnowledgeGraph(workspace_root=str(tmp_path))
    count = graph.index_directory()
    assert count >= 1

    # Check class extraction
    order_syms = graph.find_symbol("Order")
    assert len(order_syms) == 1
    assert order_syms[0].kind == SymbolKind.CLASS
    assert order_syms[0].docstring is not None
    assert "customer purchase" in order_syms[0].docstring

    # Check method extraction
    tax_syms = graph.find_symbol("Order.calculate_tax")
    assert len(tax_syms) == 1
    assert tax_syms[0].kind == SymbolKind.METHOD

    # Check context slice extraction
    slice_text = graph.get_context_slice(["Order", "process_order"])
    assert "class Order" in slice_text
    assert "def process_order" in slice_text


def test_git_worktree_and_pull_request(tmp_path):
    mgr = GitWorktreeManager(repo_path=str(tmp_path))
    worktree_path = mgr.create_pod_worktree(SubsystemClass.BACKEND, "feat/backend-test")
    assert worktree_path.exists()

    mgr.remove_worktree(worktree_path)
    assert not worktree_path.exists()

    pr_gen = PullRequestGenerator()
    task = Task(
        id="TASK-99",
        title="Implement Checkout",
        description="Checkout flow",
        assigned_pod=SubsystemClass.BACKEND,
    )
    test_report = TestReport(id="TR-1", task_id="TASK-99", test_suite="unit", passed_all=True)

    pr = pr_gen.generate_pr(task=task, source_branch="feat/backend-test", test_report=test_report)
    assert pr.pr_id == "PR-TASK-99"
    assert "100% Passed" in pr.description_markdown
    assert "ADR-001" in pr.description_markdown

    # Test publish_remote_pr with local fallback
    pr_gen_repo = PullRequestGenerator(repo_path=str(tmp_path))
    res = pr_gen_repo.publish_remote_pr(pr, push_to_remote=False, create_github_pr=False)
    assert res.pr_id == "PR-TASK-99"
    assert (tmp_path / "PULL_REQUEST.md").exists()
    assert "feat(backend): Implement Checkout" in (tmp_path / "PULL_REQUEST.md").read_text(encoding="utf-8")


def test_otlp_trace_exporter(tmp_path):
    out_file = tmp_path / "traces.jsonl"
    exporter = OTLPTraceExporter(output_file_path=str(out_file))

    span = TraceSpan(
        task_id="TASK-001",
        agent_name="BackendAgent",
        agent_role="BackendEngineerAgent",
        operation="CompileService",
        prompt_tokens=500,
        candidate_tokens=250,
        thinking_tokens=1000,
        duration_ms=45.2,
        status="OK",
    )

    otlp_span = exporter.format_span_to_otlp(span)
    assert otlp_span["name"] == "BackendEngineerAgent.CompileService"
    assert otlp_span["status"]["code"] == 1

    success = exporter.export_spans([span])
    assert success is True
    assert out_file.exists()
    assert "mas.tracer" in out_file.read_text(encoding="utf-8")
