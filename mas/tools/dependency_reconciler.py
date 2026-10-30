"""
Automated Dependency Detection & Reconciliation Engine for MAS.
Inspects synthesized code artifacts across polyglot ecosystems (Python, Node/TypeScript),
identifies third-party imports, checks existing project manifests (pyproject.toml, requirements.txt, package.json),
and reconciles missing dependencies.
"""

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class ReconciliationReport(BaseModel):
    file_path: str
    detected_imports: List[str] = Field(default_factory=list)
    missing_dependencies: List[str] = Field(default_factory=list)
    reconciled_manifest: Optional[str] = None
    success: bool = True
    message: str = ""


class DependencyReconciler:
    # Common Python module-to-package mappings
    PYTHON_PACKAGE_MAP: Dict[str, str] = {
        "yaml": "PyYAML",
        "jwt": "PyJWT",
        "PIL": "Pillow",
        "cv2": "opencv-python",
        "dateutil": "python-dateutil",
        "bs4": "beautifulsoup4",
        "dotenv": "python-dotenv",
        "psycopg2": "psycopg2-binary",
        "sklearn": "scikit-learn",
        "git": "GitPython",
        "google.protobuf": "protobuf",
    }

    NODE_BUILTINS: Set[str] = {
        "fs",
        "fs/promises",
        "path",
        "http",
        "https",
        "crypto",
        "os",
        "stream",
        "events",
        "util",
        "child_process",
        "net",
        "tls",
        "url",
        "zlib",
        "buffer",
        "assert",
        "process",
    }

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def get_python_stdlib(self) -> Set[str]:
        if hasattr(sys, "stdlib_module_names"):
            return set(sys.stdlib_module_names)
        # Fallback standard library set
        return {
            "sys", "os", "re", "json", "ast", "uuid", "datetime", "typing",
            "pathlib", "shutil", "subprocess", "sqlite3", "io", "difflib",
            "hashlib", "time", "math", "collections", "itertools", "functools",
            "unittest", "logging", "contextlib", "abc", "enum", "dataclasses",
            "copy", "urllib", "http", "socket", "threading", "multiprocessing",
            "queue", "tempfile", "traceback", "inspect", "random", "string"
        }

    def extract_python_imports(self, code_content: str) -> Set[str]:
        """
        Parses Python code and extracts all top-level imported package names.
        """
        imports: Set[str] = set()
        try:
            tree = ast.parse(code_content)
        except Exception:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
                    imports.add(top_pkg)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_pkg = node.module.split(".")[0]
                    imports.add(top_pkg)
        return imports

    def extract_node_imports(self, code_content: str) -> Set[str]:
        """
        Extracts imported packages from TypeScript/JavaScript files.
        """
        imports: Set[str] = set()
        # Matches: import ... from 'pkg' or import 'pkg'
        pattern_import = re.compile(r"""(?:import\s+(?:[\w*\s{},]*\s+from\s+)?['"]([^'"]+)['"])""")
        # Matches: require('pkg')
        pattern_require = re.compile(r"""(?:require\s*\(\s*['"]([^'"]+)['"]\s*\))""")

        for match in pattern_import.finditer(code_content):
            target = match.group(1).strip()
            pkg = self._extract_node_package_name(target)
            if pkg:
                imports.add(pkg)

        for match in pattern_require.finditer(code_content):
            target = match.group(1).strip()
            pkg = self._extract_node_package_name(target)
            if pkg:
                imports.add(pkg)

        return imports

    def _extract_node_package_name(self, target: str) -> Optional[str]:
        if target.startswith(".") or target.startswith("/"):
            return None  # Relative import

        parts = target.split("/")
        if target.startswith("@"):
            if len(parts) >= 2:
                pkg = f"{parts[0]}/{parts[1]}"
            else:
                pkg = parts[0]
        else:
            pkg = parts[0]

        if pkg in self.NODE_BUILTINS:
            return None
        return pkg

    def find_missing_python_dependencies(
        self, imports: Set[str], project_root: Optional[Path] = None
    ) -> List[str]:
        """
        Compares imported modules against standard library and project manifests.
        """
        root = project_root or self.workspace_root
        stdlib = self.get_python_stdlib()

        # Filter out stdlib and internal packages (like 'mas')
        third_party_candidates = {
            pkg for pkg in imports if pkg not in stdlib and pkg != "mas" and not pkg.startswith("_")
        }

        # Map to canonical PyPI package names
        mapped_candidates = {
            self.PYTHON_PACKAGE_MAP.get(pkg, pkg) for pkg in third_party_candidates
        }

        # Read existing dependencies from requirements.txt or pyproject.toml
        existing_pkgs: Set[str] = set()

        req_txt = root / "requirements.txt"
        if req_txt.exists():
            for line in req_txt.read_text(encoding="utf-8").splitlines():
                clean = re.split(r"[><=~;]", line.strip())[0].strip().lower()
                if clean:
                    existing_pkgs.add(clean)

        pyproj = root / "pyproject.toml"
        if pyproj.exists():
            content = pyproj.read_text(encoding="utf-8")
            # Extract dependencies list inside pyproject.toml
            matches = re.findall(r'"([a-zA-Z0-9_\-]+)(?:[><=~;].*)?"', content)
            for m in matches:
                existing_pkgs.add(m.lower())

        missing = [
            pkg for pkg in mapped_candidates if pkg.lower() not in existing_pkgs
        ]
        return sorted(missing)

    def find_missing_node_dependencies(
        self, imports: Set[str], project_root: Optional[Path] = None
    ) -> List[str]:
        """
        Compares imported packages against package.json dependencies.
        """
        root = project_root or self.workspace_root
        pkg_json_path = root / "package.json"

        existing_deps: Set[str] = set()
        if pkg_json_path.exists():
            try:
                data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
                existing_deps.update(data.get("dependencies", {}).keys())
                existing_deps.update(data.get("devDependencies", {}).keys())
                existing_deps.update(data.get("peerDependencies", {}).keys())
            except Exception:
                pass

        missing = [pkg for pkg in imports if pkg not in existing_deps]
        return sorted(missing)

    def reconcile_python_dependencies(
        self, missing_pkgs: List[str], project_root: Optional[Path] = None
    ) -> Optional[str]:
        """
        Appends missing packages to requirements.txt (or creates it) in the project root.
        """
        if not missing_pkgs:
            return None

        root = project_root or self.workspace_root
        req_txt = root / "requirements.txt"

        existing_lines = []
        if req_txt.exists():
            existing_lines = req_txt.read_text(encoding="utf-8").splitlines()

        new_lines = list(existing_lines)
        if new_lines and new_lines[-1].strip():
            new_lines.append("")

        for pkg in missing_pkgs:
            new_lines.append(f"{pkg}>=1.0.0")

        req_txt.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return str(req_txt)

    def reconcile_node_dependencies(
        self, missing_pkgs: List[str], project_root: Optional[Path] = None
    ) -> Optional[str]:
        """
        Adds missing packages into package.json dependencies.
        Only activates if package.json already exists or if frontend project indicators are present.
        """
        if not missing_pkgs:
            return None

        root = project_root or self.workspace_root
        pkg_json_path = root / "package.json"

        # Guard against polluting pure non-frontend repos
        has_frontend = (
            pkg_json_path.exists()
            or (root / "tsconfig.json").exists()
            or (root / "frontend").is_dir()
            or (root / "components").is_dir()
        )
        if not has_frontend:
            return None

        data: Dict[str, Any] = {}
        if pkg_json_path.exists():
            try:
                data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        if "dependencies" not in data:
            data["dependencies"] = {}

        for pkg in missing_pkgs:
            if pkg not in data["dependencies"]:
                data["dependencies"][pkg] = "^latest"

        pkg_json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return str(pkg_json_path)

    def reconcile_file(
        self, file_path: str, code_content: Optional[str] = None, project_root: Optional[Path] = None
    ) -> ReconciliationReport:
        """
        End-to-end reconciliation for a single file.
        """
        root = project_root or self.workspace_root
        path_obj = Path(file_path)
        content = code_content
        if content is None:
            full_path = root / file_path if not path_obj.is_absolute() else path_obj
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
            else:
                content = ""

        ext = path_obj.suffix.lower()

        if ext in (".py", ".pyw"):
            imports = self.extract_python_imports(content)
            missing = self.find_missing_python_dependencies(imports, project_root=root)
            reconciled = None
            if missing:
                reconciled = self.reconcile_python_dependencies(missing, project_root=root)
            return ReconciliationReport(
                file_path=file_path,
                detected_imports=sorted(list(imports)),
                missing_dependencies=missing,
                reconciled_manifest=reconciled,
                success=True,
                message=f"Reconciled {len(missing)} Python packages into {reconciled}" if missing else "Dependencies up to date.",
            )

        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            imports = self.extract_node_imports(content)
            missing = self.find_missing_node_dependencies(imports, project_root=root)
            reconciled = None
            if missing:
                reconciled = self.reconcile_node_dependencies(missing, project_root=root)
            return ReconciliationReport(
                file_path=file_path,
                detected_imports=sorted(list(imports)),
                missing_dependencies=missing,
                reconciled_manifest=reconciled,
                success=True,
                message=f"Reconciled {len(missing)} Node packages into {reconciled}" if missing else "Dependencies up to date.",
            )

        return ReconciliationReport(
            file_path=file_path,
            detected_imports=[],
            missing_dependencies=[],
            success=True,
            message="No dependency reconciliation needed for file type.",
        )
