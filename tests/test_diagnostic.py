"""
Unit and Integration Verification for In-Cockpit Test Failure Auto-Diagnostic & Auto-Fix.
Validates failure parsing, defect line extraction, pod classification,
autonomous ReAct self-healing, and REST API endpoints.
"""

import json
import threading
import urllib.request

from mas.api.server import start_mas_web_server
from mas.core.diagnostic import (
    TestFailureDiagnostic,
    determine_assigned_pod,
    execute_autofix_pipeline,
    parse_pytest_failure,
)


def test_parse_pytest_failure_success():
    diagnostic = parse_pytest_failure(stdout="5 passed in 0.22s", stderr="", exit_code=0)
    assert diagnostic.has_failure is False


def test_parse_pytest_failure_error_extraction():
    pytest_log = """
=================================== FAILURES ===================================
_______________________________ test_create_order _______________________________
    def test_create_order():
>       assert response.status_code == 200
E       AssertionError: assert 500 == 200
File "artifacts/code_patch/service.py", line 42, in create_order
=========================== short test summary info ============================
FAILED artifacts/code_patch/test_service.py::test_create_order - AssertionError: assert 500 == 200
============================== 1 failed in 0.45s ===============================
"""
    diagnostic = parse_pytest_failure(stdout=pytest_log, stderr="", exit_code=1)

    assert diagnostic.has_failure is True
    assert diagnostic.error_type == "AssertionError"
    assert "assert 500 == 200" in diagnostic.failure_summary
    assert diagnostic.failed_test == "artifacts/code_patch/test_service.py::test_create_order"
    assert diagnostic.target_file == "artifacts/code_patch/service.py"
    assert diagnostic.line_number == 42
    assert diagnostic.assigned_pod == "Backend Pod"


def test_pod_assignment_classification():
    assert determine_assigned_pod("db/schema.sql") == "Data Pod"
    assert determine_assigned_pod("frontend/ResourceView.tsx") == "Frontend Pod"
    assert determine_assigned_pod("deploy/Dockerfile") == "Cloud & SRE Pod"
    assert determine_assigned_pod("tests/test_audit.py") == "Governance & QA"
    assert determine_assigned_pod("mas/services/order.py") == "Backend Pod"


def test_execute_autofix_pipeline_mock():
    diag = TestFailureDiagnostic(
        has_failure=True,
        failure_summary="AssertionError: assert 500 == 200",
        target_file="artifacts/code_patch/service.py",
        assigned_pod="Backend Pod",
        line_number=42,
    )

    result = execute_autofix_pipeline(
        mission_id="test-autofix-1",
        diagnostic=diag,
        workspace_root=".",
    )

    assert result.mission_id == "test-autofix-1"
    assert result.target_file == "artifacts/code_patch/service.py"
    assert result.assigned_pod == "Backend Pod"
    assert result.status in ("RESOLVED", "PATCH_APPLIED")
    assert result.react_turns_count >= 1
    assert "Autonomous Auto-Fix (Backend Pod)" in result.message


def test_autofix_api_endpoints_via_http():
    server = start_mas_web_server(host="127.0.0.1", port=0)
    assigned_port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    base_url = f"http://127.0.0.1:{assigned_port}"

    try:
        # 1. Create mission
        create_payload = json.dumps(
            {
                "title": "Diagnostic AutoFix Mission",
                "description": "Integration test for auto diagnostic",
                "interactive": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/v1/missions",
            data=create_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 201
            created = json.loads(resp.read().decode("utf-8"))
            mid = created["mission_id"]

        # 2. Test Run endpoint returns diagnostic field
        run_req = urllib.request.Request(
            f"{base_url}/api/v1/missions/{mid}/tests/run",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(run_req) as resp:
            assert resp.status == 200
            run_data = json.loads(resp.read().decode("utf-8"))
            assert "diagnostic" in run_data
            assert "has_failure" in run_data["diagnostic"]

        # 3. Autofix endpoint dispatches self-healing ReAct loop
        autofix_payload = json.dumps(
            {
                "failure_summary": "AssertionError: expected status 200, got 500",
                "target_file": "artifacts/code_patch/service.py",
                "assigned_pod": "Backend Pod",
            }
        ).encode("utf-8")
        fix_req = urllib.request.Request(
            f"{base_url}/api/v1/missions/{mid}/tests/autofix",
            data=autofix_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(fix_req) as resp:
            assert resp.status == 200
            fix_data = json.loads(resp.read().decode("utf-8"))
            assert fix_data["status"] in ("RESOLVED", "PATCH_APPLIED")
            assert fix_data["assigned_pod"] == "Backend Pod"
            assert fix_data["react_turns_count"] >= 1
            assert "retest_status" in fix_data
    finally:
        server.shutdown()
        server.server_close()

