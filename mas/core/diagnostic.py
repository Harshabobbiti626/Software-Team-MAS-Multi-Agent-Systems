"""
Test Failure Diagnostic Parser & Autonomous Auto-Fix Engine.
Extracts failing assertions, stack traces, and defect locations from pytest runs,
and orchestrates the ReAct self-healing loop to diagnose, patch, and verify code.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from mas.core.config import get_config
from mas.core.llm import DeterministicMockLLMProvider, GeminiRESTProvider
from mas.core.react_engine import AutonomousReActEngine, ReActToolbox
from mas.tools.sandbox import SubprocessSandbox


class TestFailureDiagnostic(BaseModel):
    __test__ = False
    has_failure: bool
    failure_summary: str = ""
    error_type: str = ""
    failed_test: str = ""
    target_file: str = "artifacts/code_patch/service.py"
    line_number: Optional[int] = None
    assigned_pod: str = "Backend Pod"
    raw_traceback: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutoFixResult(BaseModel):
    status: str  # "RESOLVED", "PATCH_APPLIED", "FAILED"
    mission_id: str
    target_file: str
    assigned_pod: str
    diagnostic_summary: str
    react_turns_count: int = 0
    retest_exit_code: int = 0
    retest_status: str = "PASSED"
    message: str = ""


def determine_assigned_pod(file_path: str) -> str:
    """Classifies which engineering pod owns the target failure file."""
    f = file_path.lower()
    if f.endswith(".sql") or "schema" in f or "migration" in f:
        return "Data Pod"
    if f.endswith(".tsx") or f.endswith(".jsx") or "view" in f or "component" in f:
        return "Frontend Pod"
    if "dockerfile" in f or f.endswith(".tf") or "helm" in f or "deploy" in f:
        return "Cloud & SRE Pod"
    if "test_" in f or "_test" in f or "testreport" in f:
        return "Governance & QA"
    return "Backend Pod"


def parse_pytest_failure(
    stdout: str,
    stderr: str = "",
    exit_code: int = 0,
    default_file: Optional[str] = None,
) -> TestFailureDiagnostic:
    """
    Extracts root cause, failing test name, target defect file, and responsible pod from pytest logs.
    """
    if exit_code == 0 and not stderr:
        return TestFailureDiagnostic(has_failure=False)

    combined = f"{stdout}\n{stderr}"

    # 1. Extract failing test name (e.g. FAILED artifacts/code_patch/test_service.py::test_create)
    failed_test = ""
    failed_match = re.search(r"FAILED\s+([^\s:]+::[^\s]+)", combined)
    if failed_match:
        failed_test = failed_match.group(1).strip()
    else:
        alt_match = re.search(r"FAILED\s+([^\s]+)", combined)
        if alt_match:
            failed_test = alt_match.group(1).strip()

    # 2. Extract error type and message (e.g., AssertionError: ..., NameError: ...)
    error_type = "AssertionError"
    failure_summary = "Test assertion or boundary condition failed"

    err_match = re.search(
        r"([A-Z][a-zA-Z0-9_]*(?:Error|Exception|Failure)):\s*(.*)",
        combined,
    )
    if err_match:
        error_type = err_match.group(1).strip()
        failure_summary = f"{error_type}: {err_match.group(2).strip()}"
    elif "assert " in combined:
        assert_match = re.search(r"(assert\s+.*)", combined)
        if assert_match:
            failure_summary = f"AssertionError: {assert_match.group(1).strip()[:140]}"

    # 3. Locate defect file and line number
    target_file = default_file or "artifacts/code_patch/service.py"
    line_number = None

    file_line_match = re.search(r'File "([^"]+)", line (\d+)', combined)
    if file_line_match:
        f_cand = file_line_match.group(1).replace("\\", "/")
        if "site-packages" not in f_cand and ("artifacts" in f_cand or "mas" in f_cand):
            target_file = f_cand
            line_number = int(file_line_match.group(2))

    # Fallback to test file if test itself failed
    if not target_file and failed_test:
        target_file = failed_test.split("::")[0]

    assigned_pod = determine_assigned_pod(target_file)

    return TestFailureDiagnostic(
        has_failure=True,
        failure_summary=failure_summary,
        error_type=error_type,
        failed_test=failed_test,
        target_file=target_file,
        line_number=line_number,
        assigned_pod=assigned_pod,
        raw_traceback=combined[-1200:],
    )


def execute_autofix_pipeline(
    mission_id: str,
    diagnostic: TestFailureDiagnostic,
    workspace_root: str = ".",
    session: Optional[Any] = None,
) -> AutoFixResult:
    """
    Executes autonomous self-healing ReAct loop to repair defects identified by pytest.
    """
    root = Path(workspace_root).resolve()

    config = get_config()
    api_key = config.models.api_key

    # Initialize resilient LLM provider
    if api_key and not config.system.deterministic_mode:
        llm = GeminiRESTProvider(api_key=api_key, default_model=config.models.default_model)
    else:
        llm = DeterministicMockLLMProvider(default_model="gemini-3.5-flash-lite")

    blackboard = getattr(session, "blackboard", None)
    toolbox = ReActToolbox(workspace_root=str(root), blackboard=blackboard)
    engine = AutonomousReActEngine(llm=llm, toolbox=toolbox, max_turns=4)

    role_mapping = {
        "Data Pod": "DatabaseArchitectAgent",
        "Frontend Pod": "FrontendEngineerAgent",
        "Cloud & SRE Pod": "DevOpsSREAgent",
        "Governance & QA": "QASDETAgent",
        "Backend Pod": "BackendEngineerAgent",
    }
    agent_role = role_mapping.get(diagnostic.assigned_pod, "BackendEngineerAgent")

    objective = (
        f"Diagnose and repair test failure in '{diagnostic.target_file}': {diagnostic.failure_summary}. "
        f"Inspect the code, verify syntax with 'ast_syntax_check', and fix the failure."
    )

    react_res = engine.execute_loop(
        role=agent_role,
        task_title=f"Auto-Fix Test Failure ({diagnostic.assigned_pod})",
        task_description=objective,
    )

    # Re-run sandboxed pytest to verify that fix resolves the defect
    sandbox = SubprocessSandbox(workspace_root=str(root))
    retest_target = "artifacts/code_patch"
    test_files = list((root / "artifacts" / "code_patch").glob("test_*.py"))
    if test_files:
        retest_target = str(test_files[0].relative_to(root)).replace("\\", "/")

    sandbox_res = sandbox.execute(["pytest", "-v", retest_target])
    retest_status = "PASSED" if sandbox_res.exit_code == 0 else "FAILED"
    status = "RESOLVED" if retest_status == "PASSED" else "PATCH_APPLIED"

    msg = (
        f"Autonomous Auto-Fix ({diagnostic.assigned_pod}): {status}. "
        f"ReAct executed {len(react_res.turns)} turns. "
        f"Sandboxed verification re-test: {retest_status} (exit code {sandbox_res.exit_code})."
    )

    return AutoFixResult(
        status=status,
        mission_id=mission_id,
        target_file=diagnostic.target_file,
        assigned_pod=diagnostic.assigned_pod,
        diagnostic_summary=diagnostic.failure_summary,
        react_turns_count=len(react_res.turns),
        retest_exit_code=sandbox_res.exit_code,
        retest_status=retest_status,
        message=msg,
    )
