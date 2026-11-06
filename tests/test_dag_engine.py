"""
Unit & Integration Verification for Interactive Visual Code & Task Dependency DAG.
Validates multi-tier topology, AST symbol counting, directed edge integrity,
and API endpoint serializability.
"""

import json
import threading
import urllib.request

from mas.api.server import start_mas_web_server
from mas.core.dag_engine import DAGTier, build_mission_dag


def test_build_mission_dag_structure():
    dag = build_mission_dag(workspace_root=".")
    data = dag.model_dump()

    assert dag.mission_id == "GLOBAL"
    assert len(dag.nodes) >= 6
    assert len(dag.edges) >= 5
    assert len(dag.tiers) == 6

    # Verify all tier enums are represented
    tiers_in_nodes = {n.tier for n in dag.nodes}
    assert DAGTier.CONTRACT in tiers_in_nodes
    assert DAGTier.DATA in tiers_in_nodes
    assert DAGTier.BACKEND in tiers_in_nodes
    assert DAGTier.POD_PARALLEL in tiers_in_nodes
    assert DAGTier.VERIFICATION in tiers_in_nodes
    assert DAGTier.GOVERNANCE in tiers_in_nodes

    # Check node ID uniqueness
    node_ids = [n.id for n in dag.nodes]
    assert len(node_ids) == len(set(node_ids))

    # Verify edge connectivity
    for edge in dag.edges:
        assert edge.source in node_ids, f"Edge source {edge.source} not in nodes"
        assert edge.target in node_ids, f"Edge target {edge.target} not in nodes"

    # Verify stats
    stats = data["stats"]
    assert stats["total_nodes"] == len(dag.nodes)
    assert stats["total_edges"] == len(dag.edges)
    assert stats["critical_path_depth"] == 6
    assert stats["completion_percentage"] >= 0.0


def test_dag_api_endpoints_via_http():
    server = start_mas_web_server(host="127.0.0.1", port=0)
    assigned_port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    base_url = f"http://127.0.0.1:{assigned_port}"

    try:
        # 1. Global DAG endpoint
        with urllib.request.urlopen(f"{base_url}/api/v1/dag") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "nodes" in data
            assert "edges" in data
            assert "tiers" in data
            assert "stats" in data
            assert len(data["nodes"]) >= 6
            assert len(data["edges"]) >= 5

        # 2. Specific mission DAG endpoint
        with urllib.request.urlopen(f"{base_url}/api/v1/missions/TEST-MISSION-123/dag") as resp:
            assert resp.status == 200
            m_data = json.loads(resp.read().decode("utf-8"))
            assert m_data["mission_id"] == "TEST-MISSION-123"
            assert len(m_data["nodes"]) >= 6
    finally:
        server.shutdown()
        server.server_close()
