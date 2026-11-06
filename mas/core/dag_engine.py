"""
Interactive Visual Code & Task Dependency DAG Engine.
Builds multi-tier dependency topology connecting PRD specifications,
architecture contracts, database schemas, parallel pod deliverables,
and QA verification suites with AST-aware code symbol metadata.
"""

import ast
import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DAGTier(str, Enum):
    CONTRACT = "contract"
    DATA = "data"
    BACKEND = "backend"
    POD_PARALLEL = "pod_parallel"
    VERIFICATION = "verification"
    GOVERNANCE = "governance"


class DAGNode(BaseModel):
    id: str
    label: str
    name: str
    tier: DAGTier
    tier_order: int
    stage: str
    role: str
    pod: str
    status: str  # "COMPLETED", "IN_PROGRESS", "PENDING", "VERIFIED"
    path: Optional[str] = None
    artifact_id: Optional[str] = None
    description: str
    symbols_count: int = 0
    line_count: int = 0
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DAGEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relationship: str = "DEPENDS_ON"


class DAGGraph(BaseModel):
    mission_id: str
    title: str
    stage: str
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    tiers: List[Dict[str, Any]]
    stats: Dict[str, Any]


def _count_ast_symbols(file_path: Path) -> int:
    """Safely inspects a python file for class and function symbol counts."""
    if not file_path.is_file() or not file_path.name.endswith(".py"):
        return 0
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                count += 1
        return count
    except Exception:
        return 0


def _count_lines(file_path: Path) -> int:
    """Counts lines in a file safely."""
    if not file_path.is_file():
        return 0
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return len(content.splitlines())
    except Exception:
        return 0


def build_mission_dag(
    session: Optional[Any] = None,
    workspace_root: str = ".",
    mission_id: Optional[str] = None,
) -> DAGGraph:
    """
    Constructs a comprehensive, interactive task & code dependency DAG for the given mission.
    Synthesizes live blackboard artifacts, filesystem deliverables, and TaskDAG parallel workstreams.
    """
    root = Path(workspace_root).resolve()
    mid = mission_id or (session.mission_id if session else "GLOBAL")
    title = session.title if session else "Multi-Agent System Dependency Workbench"
    stage = session.current_stage if session else "PARALLEL_PODS"

    # Default DAG Template Node Definitions
    raw_nodes = [
        # Tier 1: Contracts & Specifications
        {
            "id": "node-prd",
            "label": "ProjectCharter.json",
            "name": "PRD & Charter Specification",
            "tier": DAGTier.CONTRACT,
            "tier_order": 1,
            "stage": "BUSINESS",
            "role": "ProductManagerAgent",
            "pod": "Leadership",
            "description": "Executive scope, problem definition & INVEST user stories",
            "dependencies": [],
            "candidate_paths": [
                "artifacts/prd/ProjectCharter.json",
                "artifacts/prd/PRD.md",
            ],
            "fallback_id": "art-ProjectCharter-json",
            "edge_label": "decomposes into",
        },
        {
            "id": "node-adr",
            "label": "ADR-001.md",
            "name": "Architecture Decision Record",
            "tier": DAGTier.CONTRACT,
            "tier_order": 1,
            "stage": "ARCHITECTURE",
            "role": "SystemArchitectAgent",
            "pod": "Architecture",
            "description": "Clean architecture topology, non-goals & pre-mortem failure mode analysis",
            "dependencies": ["node-prd"],
            "candidate_paths": ["artifacts/adr/ADR-001.md"],
            "fallback_id": "art-ADR-001-md",
            "edge_label": "defines architecture for",
        },
        {
            "id": "node-dag",
            "label": "TaskDAG.json",
            "name": "Parallel Execution DAG",
            "tier": DAGTier.CONTRACT,
            "tier_order": 1,
            "stage": "ARCHITECTURE",
            "role": "TechLeadAgent",
            "pod": "Architecture",
            "description": "Contract-first workstream decomposition with dependency constraints",
            "dependencies": ["node-adr"],
            "candidate_paths": ["artifacts/prd/TaskDAG.json"],
            "fallback_id": "art-TaskDAG-json",
            "edge_label": "locks contracts for",
        },
        {
            "id": "node-api-spec",
            "label": "api-spec.yaml",
            "name": "OpenAPI Specification",
            "tier": DAGTier.CONTRACT,
            "tier_order": 1,
            "stage": "ARCHITECTURE",
            "role": "TechLeadAgent",
            "pod": "Architecture",
            "description": "Strict REST contract definitions with RFC 7807 problem details",
            "dependencies": ["node-dag"],
            "candidate_paths": ["artifacts/api_spec/api-spec.yaml"],
            "fallback_id": "art-api-spec-yaml",
            "edge_label": "models tables from",
        },
        # Tier 2: Schemas & Data Models
        {
            "id": "node-schema",
            "label": "schema.sql",
            "name": "PostgreSQL DDL & Indexing",
            "tier": DAGTier.DATA,
            "tier_order": 2,
            "stage": "PARALLEL_PODS",
            "role": "DatabaseArchitectAgent",
            "pod": "Data Pod",
            "description": "Normalized 3NF relational schema, foreign keys & B-tree indexes",
            "dependencies": ["node-api-spec"],
            "candidate_paths": [
                "artifacts/schema_sql/schema.sql",
                "artifacts/schema_sql/schema_resource.sql",
            ],
            "fallback_id": "art-schema-sql",
            "edge_label": "queries & maps",
        },
        # Tier 3: Core Backend & API Services
        {
            "id": "node-backend",
            "label": "service.py",
            "name": "FastAPI Domain Service",
            "tier": DAGTier.BACKEND,
            "tier_order": 3,
            "stage": "PARALLEL_PODS",
            "role": "BackendEngineerAgent",
            "pod": "Backend Pod",
            "description": "REST endpoints, Pydantic v2 schemas & circuit breaker resilience",
            "dependencies": ["node-schema"],
            "candidate_paths": [
                "artifacts/code_patch/service.py",
                "artifacts/code_patch/resource_service.py",
                "artifacts/artifacts/code_patch/service.py",
            ],
            "fallback_id": "art-service-py",
            "edge_label": "serves API to",
        },
        # Tier 4: Parallel Pod Deliverables (Frontend & Cloud)
        {
            "id": "node-frontend",
            "label": "IntegrationView.tsx",
            "name": "Accessible React 4-State UI",
            "tier": DAGTier.POD_PARALLEL,
            "tier_order": 4,
            "stage": "PARALLEL_PODS",
            "role": "FrontendEngineerAgent",
            "pod": "Frontend Pod",
            "description": "WCAG 2.1 AA compliant UI with loading, empty, error & data states",
            "dependencies": ["node-backend"],
            "candidate_paths": [
                "artifacts/code_patch/IntegrationView.tsx",
                "artifacts/code_patch/ResourceView.tsx",
                "artifacts/code_patch/CoreView.tsx",
                "artifacts/code_patch/PaymentView.tsx",
            ],
            "fallback_id": "art-IntegrationView-tsx",
            "edge_label": "tested alongside",
        },
        {
            "id": "node-cloud",
            "label": "Dockerfile & main.tf",
            "name": "Distroless Container & IaC",
            "tier": DAGTier.POD_PARALLEL,
            "tier_order": 4,
            "stage": "PARALLEL_PODS",
            "role": "DevOpsSREAgent",
            "pod": "Cloud & SRE Pod",
            "description": "Hardened multi-stage Docker build & Terraform AWS/GCP infrastructure",
            "dependencies": ["node-backend"],
            "candidate_paths": [
                "artifacts/code_patch/Dockerfile",
                "artifacts/code_patch/main.tf",
            ],
            "fallback_id": "art-Dockerfile",
            "edge_label": "deploys service",
        },
        # Tier 5: Quality Assurance & Verification
        {
            "id": "node-qa",
            "label": "test_service.py",
            "name": "Pytest Verification Suite",
            "tier": DAGTier.VERIFICATION,
            "tier_order": 5,
            "stage": "VERIFICATION",
            "role": "QASDETAgent",
            "pod": "Governance & QA",
            "description": "Happy path, fault-injection & boundary condition test coverage",
            "dependencies": ["node-backend", "node-frontend"],
            "candidate_paths": [
                "artifacts/code_patch/test_service.py",
                "artifacts/code_patch/test_resource.py",
            ],
            "fallback_id": "art-test_service-py",
            "edge_label": "aggregates into",
        },
        {
            "id": "node-report",
            "label": "TestReport.json",
            "name": "Automated Test Dossier",
            "tier": DAGTier.VERIFICATION,
            "tier_order": 5,
            "stage": "VERIFICATION",
            "role": "QASDETAgent",
            "pod": "Governance & QA",
            "description": "Deterministic test run verdict, exit code & execution duration",
            "dependencies": ["node-qa"],
            "candidate_paths": ["artifacts/test_report/TestReport.json"],
            "fallback_id": "art-TestReport-json",
            "edge_label": "audited by",
        },
        # Tier 6: Governance & Security Audit
        {
            "id": "node-audit",
            "label": "SecurityAuditReport.json",
            "name": "Security & Architecture Audit",
            "tier": DAGTier.GOVERNANCE,
            "tier_order": 6,
            "stage": "GOVERNANCE",
            "role": "SystemArchitectAgent",
            "pod": "Governance & QA",
            "description": "Static code analysis, OWASP vulnerability check & review decisions",
            "dependencies": ["node-report"],
            "candidate_paths": [
                "artifacts/security_audit/SecurityAuditReport.json",
                "artifacts/audit_dossier/ReviewDecision.json",
            ],
            "fallback_id": "art-SecurityAuditReport-json",
            "edge_label": "approves launch",
        },
    ]

    # Dynamically match existing files and blackboard artifacts
    dag_nodes: List[DAGNode] = []
    edges: List[DAGEdge] = []

    # Map candidate paths to live files
    for raw in raw_nodes:
        resolved_path: Optional[str] = None
        resolved_artifact_id = raw["fallback_id"]
        line_cnt = 0
        symbols_cnt = 0
        status = "PENDING"

        # Check candidate file paths
        for rel_p in raw["candidate_paths"]:
            p = root / rel_p
            if p.is_file():
                resolved_path = str(p.relative_to(root)).replace("\\", "/")
                line_cnt = _count_lines(p)
                symbols_cnt = _count_ast_symbols(p)
                status = "COMPLETED"
                break

        # Check blackboard artifacts if session is provided
        if session and hasattr(session, "blackboard"):
            for art in session.blackboard.list_artifacts():
                art_name = art.name.lower()
                expected_label = raw["label"].lower()
                if (
                    expected_label in art_name
                    or (art.path and any(cp in art.path for cp in raw["candidate_paths"]))
                ):
                    resolved_artifact_id = art.id
                    if art.path:
                        resolved_path = art.path
                    if art.content:
                        line_cnt = max(line_cnt, len(art.content.splitlines()))
                        status = "COMPLETED"
                    break

        # If live pod is currently running
        if session and hasattr(session, "pod_statuses"):
            pod_info = session.pod_statuses.get(raw["pod"], {})
            if pod_info.get("status") == "RUNNING":
                status = "IN_PROGRESS"

        # Mark QA as VERIFIED if completed
        if raw["tier"] == DAGTier.VERIFICATION and status == "COMPLETED":
            status = "VERIFIED"

        node = DAGNode(
            id=raw["id"],
            label=raw["label"],
            name=raw["name"],
            tier=raw["tier"],
            tier_order=raw["tier_order"],
            stage=raw["stage"],
            role=raw["role"],
            pod=raw["pod"],
            status=status,
            path=resolved_path,
            artifact_id=resolved_artifact_id,
            description=raw["description"],
            symbols_count=symbols_cnt,
            line_count=line_cnt,
            dependencies=raw["dependencies"],
            metadata={"edge_label": raw.get("edge_label", "depends on")},
        )
        dag_nodes.append(node)

    # Build directed edges
    for n in dag_nodes:
        for dep_id in n.dependencies:
            edge_id = f"edge-{dep_id}-{n.id}"
            parent_node = next((item for item in dag_nodes if item.id == dep_id), None)
            lbl = parent_node.metadata.get("edge_label", "depends on") if parent_node else "depends on"
            edges.append(
                DAGEdge(
                    id=edge_id,
                    source=dep_id,
                    target=n.id,
                    label=lbl,
                )
            )

    # Also parse TaskDAG.json if present to overlay custom dependencies
    task_dag_file = root / "artifacts" / "prd" / "TaskDAG.json"
    if task_dag_file.is_file():
        try:
            with open(task_dag_file, "r", encoding="utf-8") as f:
                task_dag_data = json.load(f)
            # Add metadata about parallel workstreams
            if "parallel_workstreams" in task_dag_data:
                for n in dag_nodes:
                    if n.id == "node-dag":
                        n.metadata["parallel_workstreams_count"] = len(
                            task_dag_data["parallel_workstreams"]
                        )
        except Exception:
            pass

    # Tier column definitions
    tiers_meta = [
        {
            "id": DAGTier.CONTRACT.value,
            "title": "1. Contracts & Specs",
            "color": "#38bdf8",
            "bg": "rgba(56, 189, 248, 0.1)",
        },
        {
            "id": DAGTier.DATA.value,
            "title": "2. Data & Schemas",
            "color": "#f59e0b",
            "bg": "rgba(245, 158, 11, 0.1)",
        },
        {
            "id": DAGTier.BACKEND.value,
            "title": "3. Core Backend",
            "color": "#06b6d4",
            "bg": "rgba(6, 182, 212, 0.1)",
        },
        {
            "id": DAGTier.POD_PARALLEL.value,
            "title": "4. Pod Deliverables (FE & Cloud)",
            "color": "#10b981",
            "bg": "rgba(16, 185, 129, 0.1)",
        },
        {
            "id": DAGTier.VERIFICATION.value,
            "title": "5. QA & Verification",
            "color": "#f43f5e",
            "bg": "rgba(244, 63, 94, 0.1)",
        },
        {
            "id": DAGTier.GOVERNANCE.value,
            "title": "6. Governance & Audit",
            "color": "#a855f7",
            "bg": "rgba(168, 85, 247, 0.1)",
        },
    ]

    completed_cnt = sum(1 for n in dag_nodes if n.status in ("COMPLETED", "VERIFIED"))
    in_prog_cnt = sum(1 for n in dag_nodes if n.status == "IN_PROGRESS")

    stats = {
        "total_nodes": len(dag_nodes),
        "completed_nodes": completed_cnt,
        "in_progress_nodes": in_prog_cnt,
        "pending_nodes": len(dag_nodes) - completed_cnt - in_prog_cnt,
        "total_edges": len(edges),
        "critical_path_depth": 6,
        "completion_percentage": round(
            (completed_cnt / len(dag_nodes)) * 100 if dag_nodes else 0, 1
        ),
    }

    return DAGGraph(
        mission_id=mid,
        title=title,
        stage=stage,
        nodes=dag_nodes,
        edges=edges,
        tiers=tiers_meta,
        stats=stats,
    )

