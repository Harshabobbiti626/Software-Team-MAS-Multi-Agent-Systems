from mas.core.rfc import RFCManager
from mas.core.router import IntelligentRouter, FailureCategory
from mas.core.state import SubsystemClass


def test_rfc_consensus_flow():
    mgr = RFCManager()
    req = mgr.submit_request(
        rfc_id="RFC-001",
        requester_role="FrontendEngineerAgent",
        target_role="BackendEngineerAgent",
        topic="Pagination Strategy",
        problem_statement="Payload too large for mobile devices",
        proposed_alternatives=["Cursor pagination", "Offset limit"],
        trade_offs={"Cursor": "Better scale", "Offset": "Simpler"}
    )
    assert req.rfc_id == "RFC-001"

    resp = mgr.submit_response(
        rfc_id="RFC-001",
        responder_role="BackendEngineerAgent",
        analysis="Cursor pagination scales well with Postgres index",
        recommendation="Use cursor pagination with ?after=token"
    )
    assert resp.responder_role == "BackendEngineerAgent"

    cdr = mgr.reach_consensus(
        cdr_id="CDR-001",
        rfc_id="RFC-001",
        agreed_resolution="Adopt cursor-based pagination with 50-item pages",
        contract_updates={"api-spec.yaml": "Added cursor query parameter"}
    )
    assert cdr.id == "CDR-001"
    assert "FrontendEngineerAgent" in cdr.participants
    assert "BackendEngineerAgent" in cdr.participants


def test_intelligent_router_attribution():
    router = IntelligentRouter()

    # Contract drift test
    ticket1 = router.triage_failure(
        task_id="TASK-01",
        error_output="ValidationError: field missing in schema response 422"
    )
    assert ticket1.failure_category == FailureCategory.DESIGN_DRIFT
    assert ticket1.target_pod == SubsystemClass.BACKEND

    # Database lock test
    ticket2 = router.triage_failure(
        task_id="TASK-02",
        error_output="ERROR: deadlock detected on relation 'orders'"
    )
    assert ticket2.target_pod == SubsystemClass.DATA
    assert ticket2.assignee_role == "DatabaseArchitectAgent"
