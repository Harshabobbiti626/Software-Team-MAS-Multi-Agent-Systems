"""
Git-backed Artifact Blackboard State Engine.
Provides an immutable, versioned, contract-first artifact ledger.
Supports target repository mapping for in-place software engineering tasks.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from mas.core.state import Artifact, ArtifactType


class ArtifactBlackboard:
    def __init__(
        self,
        repo_path: str = ".",
        git_enabled: bool = True,
        target_workspace_dir: Optional[str] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.git_enabled = git_enabled
        self.target_workspace_dir = (
            Path(target_workspace_dir).resolve() if target_workspace_dir else None
        )
        self._artifacts: Dict[str, Artifact] = {}
        self._history: List[Dict[str, str]] = []

    def map_to_target_path(self, artifact_type: ArtifactType, name: str) -> Optional[Path]:
        """
        Maps an artifact to its idiomatic destination in the target workspace.
        """
        if not self.target_workspace_dir:
            return None

        target_root = self.target_workspace_dir

        if artifact_type == ArtifactType.CODE_PATCH:
            if name.endswith(".py"):
                if (target_root / "src").is_dir():
                    return target_root / "src" / name
                elif (target_root / "app").is_dir():
                    return target_root / "app" / name
                return target_root / name
            elif name.endswith((".tsx", ".jsx", ".ts", ".js")):
                for sub in [
                    "src/components",
                    "components",
                    "frontend/src/components",
                    "frontend/src",
                    "src",
                ]:
                    if (target_root / sub).is_dir():
                        return target_root / sub / name
                return target_root / "src" / "components" / name
            elif name.endswith(".tf"):
                if (target_root / "terraform").is_dir():
                    return target_root / "terraform" / name
                return target_root / name
            elif "dockerfile" in name.lower():
                return target_root / name
        elif artifact_type == ArtifactType.SCHEMA_SQL:
            for sub in ["migrations", "db/migrations", "sql", "schema"]:
                if (target_root / sub).is_dir():
                    return target_root / sub / name
            return target_root / "migrations" / name
        elif artifact_type == ArtifactType.TEST_REPORT:
            if (target_root / "tests").is_dir():
                return target_root / "tests" / name
            return target_root / name
        elif artifact_type in (ArtifactType.PRD, ArtifactType.ADR, ArtifactType.API_SPEC):
            if (target_root / "docs").is_dir():
                return target_root / "docs" / name
            return target_root / "docs" / name

        return target_root / name

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
        writes to disk, syncs to target workspace if configured, and optionally git-commits.
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

        # Write to blackboard disk ledger
        target_file = self.repo_path / rel_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Sync in-place to target repository if configured
        target_dest = self.map_to_target_path(artifact_type, name)
        if target_dest is not None:
            target_dest.parent.mkdir(parents=True, exist_ok=True)
            with open(target_dest, "w", encoding="utf-8") as f:
                f.write(content)
            artifact.metadata["target_workspace_path"] = str(target_dest)

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
