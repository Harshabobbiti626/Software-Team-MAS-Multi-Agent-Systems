"""
Unit & Integration Verification for Real-Time Token Burn & Cost Efficiency Tracker.
Validates multi-pod token allocation, Gemini caching discounts, model pricing tiers,
and REST API telemetry endpoints.
"""

import json
import threading
import urllib.request

from mas.api.server import start_mas_web_server
from mas.core.cost_tracker import compute_mission_cost_report


def test_cost_tracker_calculations():
    rep = compute_mission_cost_report()
    data = rep.model_dump()

    assert data["total_tokens"] > 0
    assert data["total_tokens"] == data["total_prompt_tokens"] + data["total_candidate_tokens"] + data["total_thinking_tokens"]
    assert data["gross_cost_usd"] >= data["net_cost_usd"]
    assert data["savings_usd"] >= 0.0
    assert 0.0 <= data["cache_hit_rate_pct"] <= 100.0
    assert 0.0 <= data["budget_consumed_pct"] <= 100.0
    assert data["burn_rate_tokens_per_turn"] > 0.0
    assert len(data["pod_breakdown"]) >= 5

    # Check each pod allocation
    for pod in data["pod_breakdown"]:
        assert pod["total_tokens"] > 0
        assert pod["cost_usd"] >= 0.0
        assert pod["model"] in ("gemini-3.5-flash-lite", "gemini-2.5-pro", "gemini-2.5-flash", "default")


def test_cost_telemetry_endpoints_via_http():
    server = start_mas_web_server(host="127.0.0.1", port=0)
    assigned_port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    base_url = f"http://127.0.0.1:{assigned_port}"

    try:
        # 1. Global /api/v1/tokens
        with urllib.request.urlopen(f"{base_url}/api/v1/tokens") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "total_tokens" in data
            assert "net_cost_usd" in data
            assert "savings_usd" in data
            assert "pod_breakdown" in data
            assert len(data["pod_breakdown"]) >= 5

        # 2. Create mission to test mission-specific endpoints
        create_payload = json.dumps(
            {
                "title": "Cost Tracking Test Mission",
                "description": "Integration test description",
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

        # 3. Mission-specific /api/v1/missions/{id}/tokens
        with urllib.request.urlopen(f"{base_url}/api/v1/missions/{mid}/tokens") as resp:
            assert resp.status == 200
            m_data = json.loads(resp.read().decode("utf-8"))
            assert m_data["mission_id"] == mid
            assert "net_cost_usd" in m_data

        # 4. Mission details endpoint includes cost_telemetry
        with urllib.request.urlopen(f"{base_url}/api/v1/missions/{mid}") as resp:
            assert resp.status == 200
            details = json.loads(resp.read().decode("utf-8"))
            assert "cost_telemetry" in details
            assert details["cost_telemetry"]["total_tokens"] > 0
    finally:
        server.shutdown()
        server.server_close()
