"""
Workspace & Artifact Symbol Indexer.
Extracts AST classes, functions, methods, API endpoints, SQL schemas, and files
to enable instantaneous, fuzzy Quick-Open symbol navigation in the Cockpit IDE.
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkspaceSymbol(BaseModel):
    __test__ = False
    name: str
    kind: str  # "class", "function", "method", "endpoint", "table", "file"
    file_path: str
    line_number: int = 1
    tier: str = "Logic"  # "API", "Data", "Frontend", "Logic", "Governance", "Cloud"
    signature: str = ""
    container_name: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


def determine_symbol_tier(file_path: str, kind: str) -> str:
    """Classifies which architectural tier a symbol belongs to."""
    f = file_path.lower().replace("\\", "/")
    if kind == "table" or f.endswith(".sql") or "schema" in f or "migration" in f:
        return "Data"
    if kind == "endpoint" or "api" in f or "route" in f or "server" in f:
        return "API"
    if f.endswith(".tsx") or f.endswith(".jsx") or "component" in f or "view" in f or f.endswith(".css"):
        return "Frontend"
    if "test_" in f or "_test" in f or "testreport" in f or "audit" in f:
        return "Governance"
    if "docker" in f or f.endswith(".tf") or "helm" in f or "deploy" in f:
        return "Cloud"
    return "Logic"


def _extract_python_symbols(file_path: Path, relative_path: str) -> List[WorkspaceSymbol]:
    symbols: List[WorkspaceSymbol] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(content)
    except Exception:
        return symbols

    for node in tree.body:
        # Classes
        if isinstance(node, ast.ClassDef):
            symbols.append(
                WorkspaceSymbol(
                    name=node.name,
                    kind="class",
                    file_path=relative_path,
                    line_number=node.lineno,
                    tier=determine_symbol_tier(relative_path, "class"),
                    signature=f"class {node.name}",
                )
            )
            # Inspect methods inside class
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        WorkspaceSymbol(
                            name=item.name,
                            kind="method",
                            file_path=relative_path,
                            line_number=item.lineno,
                            tier=determine_symbol_tier(relative_path, "method"),
                            signature=f"def {item.name}(...)",
                            container_name=node.name,
                        )
                    )

        # Top-level functions & endpoints
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_endpoint = False
            endpoint_sig = f"def {node.name}(...)"
            for deco in node.decorator_list:
                deco_repr = ast.unparse(deco) if hasattr(ast, "unparse") else ""
                if any(k in deco_repr for k in ("app.", "router.", "api.", "get", "post", "put", "delete")):
                    is_endpoint = True
                    endpoint_sig = f"@{deco_repr} -> {node.name}()"
                    break

            symbols.append(
                WorkspaceSymbol(
                    name=node.name,
                    kind="endpoint" if is_endpoint else "function",
                    file_path=relative_path,
                    line_number=node.lineno,
                    tier=determine_symbol_tier(relative_path, "endpoint" if is_endpoint else "function"),
                    signature=endpoint_sig,
                )
            )

    return symbols


def _extract_typescript_symbols(file_path: Path, relative_path: str) -> List[WorkspaceSymbol]:
    symbols: List[WorkspaceSymbol] = []
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return symbols

    for idx, line in enumerate(lines, start=1):
        s_line = line.strip()

        # React Components & exported functions
        func_match = re.search(r"export\s+(?:default\s+)?(?:function|const)\s+([A-Za-z0-9_]+)", s_line)
        if func_match:
            name = func_match.group(1)
            kind = "component" if name[0].isupper() else "function"
            symbols.append(
                WorkspaceSymbol(
                    name=name,
                    kind=kind,
                    file_path=relative_path,
                    line_number=idx,
                    tier=determine_symbol_tier(relative_path, kind),
                    signature=s_line[:60],
                )
            )
            continue

        # Interfaces & Types
        type_match = re.search(r"export\s+(?:interface|type)\s+([A-Za-z0-9_]+)", s_line)
        if type_match:
            name = type_match.group(1)
            symbols.append(
                WorkspaceSymbol(
                    name=name,
                    kind="type",
                    file_path=relative_path,
                    line_number=idx,
                    tier=determine_symbol_tier(relative_path, "type"),
                    signature=s_line[:60],
                )
            )

    return symbols


def _extract_sql_symbols(file_path: Path, relative_path: str) -> List[WorkspaceSymbol]:
    symbols: List[WorkspaceSymbol] = []
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return symbols

    for idx, line in enumerate(lines, start=1):
        s_line = line.strip()
        tbl_match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.]+)", s_line, re.IGNORECASE)
        if tbl_match:
            symbols.append(
                WorkspaceSymbol(
                    name=tbl_match.group(1).replace('"', "").replace("`", ""),
                    kind="table",
                    file_path=relative_path,
                    line_number=idx,
                    tier="Data",
                    signature=s_line[:60],
                )
            )
            continue

        view_match = re.search(r"CREATE\s+VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.]+)", s_line, re.IGNORECASE)
        if view_match:
            symbols.append(
                WorkspaceSymbol(
                    name=view_match.group(1).replace('"', "").replace("`", ""),
                    kind="view",
                    file_path=relative_path,
                    line_number=idx,
                    tier="Data",
                    signature=s_line[:60],
                )
            )

    return symbols


def index_workspace_symbols(
    workspace_root: str = ".",
    query: Optional[str] = None,
    tier_filter: Optional[str] = None,
    kind_filter: Optional[str] = None,
    limit: int = 150,
) -> List[WorkspaceSymbol]:
    """
    Scans the workspace and synthesized artifacts, generating an index of symbols and files.
    Supports fuzzy query matching and tier/kind filters.
    """
    root = Path(workspace_root).resolve()
    symbols: List[WorkspaceSymbol] = []

    target_dirs = ["artifacts", "mas", "config"]
    excluded_dirs = {".git", ".pytest_cache", "__pycache__", "node_modules", "dist", "build", ".venv", "venv"}

    candidate_files: List[Path] = []
    for d_name in target_dirs:
        d_path = root / d_name
        if not d_path.exists():
            continue
        for root_dir, dirs, files in os.walk(d_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for f in files:
                p = Path(root_dir) / f
                if p.suffix in (".py", ".tsx", ".jsx", ".ts", ".js", ".sql", ".json", ".yaml", ".yml", ".md"):
                    candidate_files.append(p)

    for p in candidate_files:
        try:
            rel_str = str(p.relative_to(root)).replace("\\", "/")
        except Exception:
            rel_str = str(p).replace("\\", "/")

        # 1. Register file itself as a navigable symbol
        symbols.append(
            WorkspaceSymbol(
                name=p.name,
                kind="file",
                file_path=rel_str,
                line_number=1,
                tier=determine_symbol_tier(rel_str, "file"),
                signature=rel_str,
            )
        )

        # 2. Extract code-level symbols based on extension
        if p.suffix == ".py":
            symbols.extend(_extract_python_symbols(p, rel_str))
        elif p.suffix in (".tsx", ".jsx", ".ts", ".js"):
            symbols.extend(_extract_typescript_symbols(p, rel_str))
        elif p.suffix == ".sql":
            symbols.extend(_extract_sql_symbols(p, rel_str))

    # Apply filters
    filtered = symbols

    if tier_filter and tier_filter.upper() != "ALL":
        filtered = [s for s in filtered if s.tier.upper() == tier_filter.upper()]

    if kind_filter and kind_filter.lower() != "all":
        filtered = [s for s in filtered if s.kind.lower() == kind_filter.lower()]

    if query and query.strip():
        q = query.lower().strip()
        filtered = [
            s for s in filtered
            if q in s.name.lower() or q in s.file_path.lower() or (s.container_name and q in s.container_name.lower())
        ]

    # Deduplicate and sort: files and exact matches first
    def sort_key(s: WorkspaceSymbol):
        exact = 0 if query and s.name.lower() == query.lower() else 1
        starts = 0 if query and s.name.lower().startswith(query.lower()) else 1
        return (exact, starts, s.kind != "file", s.name)

    filtered.sort(key=sort_key)
    return filtered[:limit]
