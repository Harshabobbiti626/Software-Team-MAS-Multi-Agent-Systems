"""
AST-Aware Code Knowledge Graph for MAS.
Parses repositories using Python AST to build symbol tables, dependency call graphs,
and compact context slices without prompt context window saturation.
"""

import ast
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class SymbolKind(str, Enum):
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    IMPORT = "IMPORT"
    MODULE = "MODULE"


class CodeSymbol(BaseModel):
    name: str
    kind: SymbolKind
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    parameters: List[str] = Field(default_factory=list)
    parent_class: Optional[str] = None
    imported_from: Optional[str] = None


class DependencyEdge(BaseModel):
    source_symbol: str
    target_symbol: str
    relationship: str  # "CALLS", "INHERITS", "IMPORTS"
    file_path: str


class CodeASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: List[CodeSymbol] = []
        self.edges: List[DependencyEdge] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        doc = ast.get_docstring(node)
        class_symbol = CodeSymbol(
            name=node.name,
            kind=SymbolKind.CLASS,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            docstring=doc
        )
        self.symbols.append(class_symbol)

        # Track inheritance edges
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.edges.append(DependencyEdge(
                    source_symbol=node.name,
                    target_symbol=base.id,
                    relationship="INHERITS",
                    file_path=self.file_path
                ))

        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._record_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._record_function(node)

    def _record_function(self, node: Any) -> None:
        doc = ast.get_docstring(node)
        params = [arg.arg for arg in node.args.args]
        kind = SymbolKind.METHOD if self.current_class else SymbolKind.FUNCTION
        full_name = f"{self.current_class}.{node.name}" if self.current_class else node.name

        symbol = CodeSymbol(
            name=full_name,
            kind=kind,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            docstring=doc,
            parameters=params,
            parent_class=self.current_class
        )
        self.symbols.append(symbol)

        # Track function calls inside function body
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    self.edges.append(DependencyEdge(
                        source_symbol=full_name,
                        target_symbol=child.func.id,
                        relationship="CALLS",
                        file_path=self.file_path
                    ))
                elif isinstance(child.func, ast.Attribute):
                    self.edges.append(DependencyEdge(
                        source_symbol=full_name,
                        target_symbol=child.func.attr,
                        relationship="CALLS",
                        file_path=self.file_path
                    ))

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            self.symbols.append(CodeSymbol(
                name=alias.name,
                kind=SymbolKind.IMPORT,
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                imported_from=alias.name
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        mod = node.module or ""
        for alias in node.names:
            self.symbols.append(CodeSymbol(
                name=alias.name,
                kind=SymbolKind.IMPORT,
                file_path=self.file_path,
                line_start=node.lineno,
                line_end=node.lineno,
                imported_from=mod
            ))
        self.generic_visit(node)


class CodeKnowledgeGraph:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.symbols: Dict[str, List[CodeSymbol]] = {}  # name -> symbols
        self.file_index: Dict[str, List[CodeSymbol]] = {}  # file_path -> symbols
        self.edges: List[DependencyEdge] = []

    def index_file(self, relative_path: str) -> None:
        full_path = (self.workspace_root / relative_path).resolve()
        if not full_path.exists() or not relative_path.endswith(".py"):
            return

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(full_path))
            visitor = CodeASTVisitor(file_path=relative_path.replace("\\", "/"))
            visitor.visit(tree)

            # Store in indices
            self.file_index[visitor.file_path] = visitor.symbols
            for s in visitor.symbols:
                if s.name not in self.symbols:
                    self.symbols[s.name] = []
                self.symbols[s.name].append(s)

            self.edges.extend(visitor.edges)
        except Exception:
            # Tolerant indexing: skips files with unparseable syntax
            pass

    def index_directory(self, root_dir: Optional[str] = None) -> int:
        """Traverses and indexes all Python files under root_dir."""
        target_root = (self.workspace_root / (root_dir or "")).resolve()
        indexed_count = 0

        for root, dirs, files in os.walk(str(target_root)):
            # Skip hidden, virtualenv, and test cache dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["venv", "__pycache__", "build", "dist", "node_modules"]]
            for file in files:
                if file.endswith(".py"):
                    full_p = Path(root) / file
                    rel_p = str(full_p.relative_to(self.workspace_root)).replace("\\", "/")
                    self.index_file(rel_p)
                    indexed_count += 1

        return indexed_count

    def find_symbol(self, name: str) -> List[CodeSymbol]:
        return self.symbols.get(name, [])

    def find_references_calling(self, target_function: str) -> List[DependencyEdge]:
        return [e for e in self.edges if e.target_symbol == target_function and e.relationship == "CALLS"]

    def get_context_slice(self, symbol_names: List[str], max_lines: int = 150) -> str:
        """
        Extracts exact targeted source lines for the requested symbols
        to feed only relevant context into the LLM prompt.
        """
        lines_out = []
        total_lines = 0

        for name in symbol_names:
            matching = self.find_symbol(name)
            for sym in matching:
                if total_lines >= max_lines:
                    break
                full_p = (self.workspace_root / sym.file_path).resolve()
                if not full_p.exists():
                    continue

                try:
                    with open(full_p, "r", encoding="utf-8") as f:
                        file_lines = f.readlines()
                    start = max(0, sym.line_start - 1)
                    end = min(len(file_lines), sym.line_end)
                    snippet = "".join(file_lines[start:end])
                    lines_out.append(f"// File: {sym.file_path} (lines {sym.line_start}-{sym.line_end})\n{snippet}")
                    total_lines += (end - start)
                except Exception:
                    pass

        return "\n\n".join(lines_out)
