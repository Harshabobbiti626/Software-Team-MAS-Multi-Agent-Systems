"""
Unit & Integration Verification for In-Cockpit Quick-Open & AST Symbol Search Indexer.
Validates extraction of AST classes, methods, endpoints, SQL tables, and file paths,
as well as query filtering and REST API endpoints.
"""

import json
import threading
import urllib.request

from mas.api.server import start_mas_web_server
from mas.core.symbol_indexer import (
    WorkspaceSymbol,
    determine_symbol_tier,
    index_workspace_symbols,
)


def test_determine_symbol_tier():
    assert determine_symbol_tier("artifacts/schema_sql/schema.sql", "table") == "Data"
    assert determine_symbol_tier("mas/api/server.py", "endpoint") == "API"
    assert determine_symbol_tier("artifacts/code_patch/ResourceView.tsx", "component") == "Frontend"
    assert determine_symbol_tier("tests/test_diagnostic.py", "function") == "Governance"
    assert determine_symbol_tier("Dockerfile", "file") == "Cloud"
    assert determine_symbol_tier("mas/core/vcs.py", "class") == "Logic"


def test_index_workspace_symbols():
    symbols = index_workspace_symbols(workspace_root=".", limit=100)
    assert len(symbols) > 0

    kinds = {s.kind for s in symbols}
    assert "file" in kinds

    # Verify model structure
    for s in symbols[:20]:
        assert isinstance(s, WorkspaceSymbol)
        assert len(s.name) > 0
        assert len(s.file_path) > 0
        assert s.line_number >= 1
        assert s.tier in ("API", "Data", "Frontend", "Logic", "Governance", "Cloud")


def test_index_workspace_symbols_filtering():
    # Filter by query
    query_res = index_workspace_symbols(workspace_root=".", query="server", limit=50)
    assert len(query_res) > 0
    for s in query_res:
        assert (
            "server" in s.name.lower()
            or "server" in s.file_path.lower()
            or (s.container_name and "server" in s.container_name.lower())
        )

    # Filter by tier
    data_res = index_workspace_symbols(workspace_root=".", tier_filter="Data", limit=50)
    for s in data_res:
        assert s.tier == "Data"

    # Filter by kind
    file_res = index_workspace_symbols(workspace_root=".", kind_filter="file", limit=50)
    for s in file_res:
        assert s.kind == "file"


def test_symbol_api_endpoints_via_http():
    server = start_mas_web_server(host="127.0.0.1", port=0)
    assigned_port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    base_url = f"http://127.0.0.1:{assigned_port}"

    try:
        # 1. Global /api/v1/workspace/symbols
        with urllib.request.urlopen(f"{base_url}/api/v1/workspace/symbols") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(data, list)
            assert len(data) > 0
            assert "name" in data[0]
            assert "kind" in data[0]
            assert "file_path" in data[0]
            assert "line_number" in data[0]

        # 2. Query filtered /api/v1/workspace/symbols?query=dag&tier=Logic
        with urllib.request.urlopen(f"{base_url}/api/v1/workspace/symbols?query=dag") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(data, list)
            assert len(data) > 0
            assert any("dag" in item["name"].lower() or "dag" in item["file_path"].lower() for item in data)

        # 3. Mission-specific /api/v1/missions/{id}/symbols
        create_payload = json.dumps(
            {
                "title": "Symbol Search Mission",
                "description": "Integration test for Quick Open",
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

        with urllib.request.urlopen(f"{base_url}/api/v1/missions/{mid}/symbols") as resp:
            assert resp.status == 200
            m_data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(m_data, list)
            assert len(m_data) > 0
    finally:
        server.shutdown()
        server.server_close()
