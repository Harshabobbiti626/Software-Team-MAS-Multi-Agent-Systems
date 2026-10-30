"""
Safe File Operations & Patch Engine for MAS.
Guarantees path traversal prevention and deterministic file diff/patch handling.
"""

import difflib
import hashlib
from pathlib import Path


class SafeFileOps:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def _resolve_safe_path(self, relative_or_abs_path: str) -> Path:
        target = (self.workspace_root / relative_or_abs_path).resolve()
        # Path traversal guard
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Access denied: path '{relative_or_abs_path}' traverses outside workspace root."
            )
        return target

    def read_file(self, file_path: str) -> str:
        safe_path = self._resolve_safe_path(file_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, file_path: str, content: str) -> str:
        safe_path = self._resolve_safe_path(file_path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(safe_path)

    def create_diff(self, file_path: str, new_content: str) -> str:
        safe_path = self._resolve_safe_path(file_path)
        old_lines = []
        if safe_path.exists():
            with open(safe_path, "r", encoding="utf-8") as f:
                old_lines = f.readlines()

        new_lines = [
            line + "\n" if not line.endswith("\n") else line for line in new_content.splitlines()
        ]
        diff = difflib.unified_diff(
            old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm=""
        )
        return "\n".join(diff)

    def compute_hash(self, file_path: str) -> str:
        safe_path = self._resolve_safe_path(file_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        hasher = hashlib.sha256()
        with open(safe_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
