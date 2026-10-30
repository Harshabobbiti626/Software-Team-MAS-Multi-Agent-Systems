"""
Git-backed Artifact Blackboard State Engine.
Provides an immutable, versioned, contract-first artifact ledger.
Agents publish, subscribe, and diff canonical artifacts rather than chatting unstructuredly.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from mas.core.state import Artifact, ArtifactType


class ArtifactBlackboard:
    def __init__(self, repo_path: str = ".", git_enabled: bool = True):
        self.repo_path = Path(repo_path).resolve()
        self.git_enabled = git_enabled
        self._artifacts: Dict[str, Artifact] = {}
        self._history: List[Dict[str, str]] = []

    def register_artifact(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        content: str,
        created_by: str,
        path: Optional[str] = None,
        commit_to_git: bool = True,
    ) -> Artifact:
        """
        Stores an artifact in the blackboard, increments its version if existing,
        and optionally writes to disk and git-commits.
        """
        version = 1
        if artifact_id in self._artifacts:
            version = self._artifacts[artifact_id].version + 1

        rel_path = path or f"artifacts/{artifact_type.value.lower()}/{name}"
        artifact = Artifact(
            id=artifact_id,
            type=artifact_type,
            name=name,
            path=rel_path,
            content=content,
            version=version,
            created_by=created_by,
        )
        self._artifacts[artifact_id] = artifact

        # Write to disk
        target_file = self.repo_path / rel_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        commit_hash = None
        if self.git_enabled and commit_to_git:
            commit_hash = self._git_commit(
                str(rel_path), f"[{artifact_type.value}] {name} (v{version}) by {created_by}"
            )
            artifact.metadata["commit_hash"] = commit_hash

        self._history.append(
            {
                "artifact_id": artifact_id,
                "version": str(version),
                "created_by": created_by,
                "commit_hash": commit_hash or "uncommitted",
                "type": artifact_type.value,
            }
        )

        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def get_by_type(self, artifact_type: ArtifactType) -> List[Artifact]:
        return [a for a in self._artifacts.values() if a.type == artifact_type]

    def list_artifacts(self) -> List[Artifact]:
        return list(self._artifacts.values())

    def get_history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def _git_commit(self, file_path: str, message: str) -> Optional[str]:
        """Performs safe, best-effort git commit for an artifact."""
        try:
            # Stage file
            subprocess.run(
                ["git", "add", file_path],
                cwd=str(self.repo_path),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            # Commit file
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.repo_path),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            # Get latest hash
            rev_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_path),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            return rev_res.stdout.strip()
        except Exception:
            return None
