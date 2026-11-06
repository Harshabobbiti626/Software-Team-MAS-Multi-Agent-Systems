"""
Unit & Integration Test Suite for MAS Web API Server and SSE Event Streaming.
"""

import json
import threading
import urllib.request

from mas.api.events import EventBus
from mas.api.server import (
    MissionRegistry,
    start_mas_web_server,
)


def test_event_bus_pub_sub():
    bus = EventBus()
    mission_id = "TEST-MISSION-001"
    q = bus.subscribe(mission_id)

    bus.publish(mission_id, "STAGE_CHANGED", {"stage": "CONTRACTS"})
    event = q.get(timeout=2)
    assert event["type"] == "STAGE_CHANGED"
    assert event["payload"]["stage"] == "CONTRACTS"

    history = bus.get_history(mission_id)
    assert len(history) == 1
    assert history[0]["payload"]["stage"] == "CONTRACTS"

    bus.unsubscribe(mission_id, q)


def test_mission_registry():
    registry = MissionRegistry()
    session = registry.create_mission(
        title="Payment Service Mission",
        description="Build secure webhook",
        target_dir=None,
        interactive=True,
    )
    assert session.mission_id.startswith("MISSION-")
    assert session.title == "Payment Service Mission"
    assert session.interactive is True

    retrieved = registry.get_mission(session.mission_id)
    assert retrieved is not None
    assert retrieved.title == "Payment Service Mission"

    missions_list = registry.list_missions()
    assert len(missions_list) >= 1
    assert any(m["mission_id"] == session.mission_id for m in missions_list)


def test_web_server_rest_endpoints(tmp_path):
    server = start_mas_web_server(host="127.0.0.1", port=0)
    assigned_port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    base_url = f"http://127.0.0.1:{assigned_port}"

    try:
        # 1. Test GET /api/v1/health
        with urllib.request.urlopen(f"{base_url}/api/v1/health") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert "version" in data

        # 2. Test GET / (Serves index.html with React 18 mount point)
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "MAS Mission Control" in html
            assert 'id="root"' in html
            assert "app.js" in html

        # 3. Test POST /api/v1/missions
        create_payload = json.dumps(
            {
                "title": "API Test Service",
                "description": "Integration test description",
                "target_dir": str(tmp_path),
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
            created_data = json.loads(resp.read().decode("utf-8"))
            mission_id = created_data["mission_id"]
            assert mission_id.startswith("MISSION-")

        # 4. Test GET /api/v1/missions
        with urllib.request.urlopen(f"{base_url}/api/v1/missions") as resp:
            assert resp.status == 200
            missions_data = json.loads(resp.read().decode("utf-8"))
            assert any(m["mission_id"] == mission_id for m in missions_data["missions"])

        # 5. Test POST /api/v1/missions/{id}/gates/gate/decision
        decision_payload = json.dumps({"decision": "APPROVED"}).encode("utf-8")
        dec_req = urllib.request.Request(
            f"{base_url}/api/v1/missions/{mission_id}/gates/gate/decision",
            data=decision_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(dec_req) as resp:
            assert resp.status == 200
            dec_data = json.loads(resp.read().decode("utf-8"))
            assert dec_data["decision"] == "APPROVED"

        # 6. Test GET /api/v1/artifacts/{id}/diff
        with urllib.request.urlopen(f"{base_url}/api/v1/artifacts/service.py/diff") as resp:
            assert resp.status == 200
            diff_data = json.loads(resp.read().decode("utf-8"))
            assert "has_diff" in diff_data
            assert "diff" in diff_data
            assert "additions_count" in diff_data

        # 7. Test PUT /api/v1/artifacts/{id} (Update file with AST verification)
        update_payload = json.dumps(
            {"content": "def test_func():\n    return 'updated'\n"}
        ).encode("utf-8")
        update_req = urllib.request.Request(
            f"{base_url}/api/v1/artifacts/service.py",
            data=update_payload,
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(update_req) as resp:
            assert resp.status == 200
            update_data = json.loads(resp.read().decode("utf-8"))
            assert update_data["status"] == "SAVED"
            assert "artifact" in update_data
            assert update_data["artifact"]["version"] >= 2

        # 8. Test PUT /api/v1/artifacts/{id} with broken Python syntax (must fail with 422)
        broken_payload = json.dumps(
            {"content": "def broken_func(\n"}
        ).encode("utf-8")
        broken_req = urllib.request.Request(
            f"{base_url}/api/v1/artifacts/service.py",
            data=broken_payload,
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        try:
            urllib.request.urlopen(broken_req)
            raise AssertionError("Should have raised HTTP 422 for syntax error")
        except urllib.error.HTTPError as err:
            assert err.code == 422

        # 9. Test GET /api/v1/artifacts/{id}/versions
        with urllib.request.urlopen(f"{base_url}/api/v1/artifacts/service.py/versions") as resp:
            assert resp.status == 200
            ver_data = json.loads(resp.read().decode())
            assert "versions" in ver_data
            assert len(ver_data["versions"]) >= 1

        # 10. Test POST /api/v1/artifacts/{id}/rollback to version 1
        rollback_payload = json.dumps({"version": 1}).encode("utf-8")
        rollback_req = urllib.request.Request(
            f"{base_url}/api/v1/artifacts/service.py/rollback",
            data=rollback_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(rollback_req) as resp:
            assert resp.status == 200
            rb_data = json.loads(resp.read().decode())
            assert rb_data["status"] == "ROLLED_BACK"
            assert rb_data["rolled_back_to"] == 1

    finally:
        server.shutdown()
        server.server_close()
