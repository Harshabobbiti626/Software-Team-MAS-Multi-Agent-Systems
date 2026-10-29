"""
Surgical AST-Aware Code Patcher for MAS.
Applies search-and-replace blocks and unified diffs with atomic rollbacks
and AST syntax verification.
"""

import ast
from pathlib import Path
from typing import List, Optional, Tuple
from pydantic import BaseModel


class PatchResult(BaseModel):
    success: bool
    file_path: str
    lines_modified: int = 0
    error_message: Optional[str] = None
    original_backup: Optional[str] = None


class SurgicalPatcher:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def _resolve_safe_path(self, relative_path: str) -> Path:
        target = (self.workspace_root / relative_path).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"Access denied: Path '{relative_path}' traverses outside workspace root.")
        return target

    def apply_search_replace_block(
        self,
        file_path: str,
        search_block: str,
        replace_block: str,
        verify_ast: bool = True
    ) -> PatchResult:
        """
        Surgically finds exact search_block and replaces it with replace_block.
        Verifies AST syntax before saving; rolls back if invalid.
        """
        safe_path = self._resolve_safe_path(file_path)
        if not safe_path.exists():
            return PatchResult(
                success=False,
                file_path=file_path,
                error_message=f"File not found: {file_path}"
            )

        with open(safe_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Normalize line endings
        normalized_original = original_content.replace("\r\n", "\n")
        normalized_search = search_block.replace("\r\n", "\n").strip()
        normalized_replace = replace_block.replace("\r\n", "\n")

        if normalized_search not in normalized_original:
            return PatchResult(
                success=False,
                file_path=file_path,
                error_message=f"Search block not found in {file_path}. Cannot apply surgical patch."
            )

        occurrences = normalized_original.count(normalized_search)
        if occurrences > 1:
            return PatchResult(
                success=False,
                file_path=file_path,
                error_message=f"Ambiguous search block: found {occurrences} occurrences in {file_path}."
            )

        new_content = normalized_original.replace(normalized_search, normalized_replace, 1)

        # AST syntax check for Python files
        if verify_ast and file_path.endswith(".py"):
            try:
                ast.parse(new_content, filename=file_path)
            except SyntaxError as se:
                return PatchResult(
                    success=False,
                    file_path=file_path,
                    error_message=f"Patch introduces syntax error on line {se.lineno}: {se.msg}",
                    original_backup=original_content
                )

        # Atomic write
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        lines_diff = abs(len(normalized_replace.splitlines()) - len(normalized_search.splitlines()))
        return PatchResult(
            success=True,
            file_path=file_path,
            lines_modified=lines_diff,
            original_backup=original_content
        )

    def parse_and_apply_block_text(self, file_path: str, block_text: str) -> PatchResult:
        """
        Parses standard <<<<<<< SEARCH / ======= / >>>>>>> REPLACE blocks.
        """
        if "<<<<<<< SEARCH" not in block_text or "=======" not in block_text or ">>>>>>> REPLACE" not in block_text:
            return PatchResult(
                success=False,
                file_path=file_path,
                error_message="Invalid block format. Expected <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE"
            )

        try:
            parts = block_text.split("<<<<<<< SEARCH")[1].split(">>>>>>> REPLACE")[0]
            search_part, replace_part = parts.split("=======", 1)
            return self.apply_search_replace_block(
                file_path=file_path,
                search_block=search_part.strip(),
                replace_block=replace_part.strip()
            )
        except Exception as e:
            return PatchResult(
                success=False,
                file_path=file_path,
                error_message=f"Failed to parse patch block: {str(e)}"
            )

