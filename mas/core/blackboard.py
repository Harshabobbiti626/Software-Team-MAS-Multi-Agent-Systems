"""
Git-backed Artifact Blackboard State Engine.
Provides an immutable, versioned, contract-first artifact ledger.
Supports target repository mapping for in-place software engineering tasks.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mas.core.state import Artifact, ArtifactType


class ArtifactBlackboard:
    def __init__(
        self,
        repo_path: str = ".",
        git_enabled: bool = True,
        target_workspace_dir: Optional[str] = None,
        hydrate_from_disk: bool = True,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.git_enabled = git_enabled
        self.target_workspace_dir = (
            Path(target_workspace_dir).resolve() if target_workspace_dir else None
        )
        self._artifacts: Dict[str, Artifact] = {}
        self._history: List[Dict[str, str]] = []
        self.on_artifact_registered: Optional[Callable[[Artifact], None]] = None

        if hydrate_from_disk:
            self.scan_and_hydrate_disk_artifacts()

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
        history: List[Dict[str, Any]] = []
        if artifact_id in self._artifacts:
            prev_art = self._artifacts[artifact_id]
            version = prev_art.version + 1
            history = list(prev_art.version_history)
            if not history:
                history.append({
                    "version": prev_art.version,
                    "content": prev_art.content,
                    "created_by": prev_art.created_by,
                    "timestamp": prev_art.created_at.isoformat(),
                })

        history.append({
            "version": version,
            "content": content,
            "created_by": created_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        rel_path = path or f"artifacts/{artifact_type.value.lower()}/{name}"
        artifact = Artifact(
            id=artifact_id,
            type=artifact_type,
            name=name,
            path=rel_path,
            content=content,
            version=version,
            created_by=created_by,
            version_history=history,
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

        if self.on_artifact_registered:
            try:
                self.on_artifact_registered(artifact)
            except Exception:
                pass

        return artifact

    def scan_and_hydrate_disk_artifacts(self) -> None:
        """
        Scans the local artifacts directory and hydrates existing disk artifacts
        into in-memory cache so they are immediately accessible to Web Cockpit and API.
        """
        artifacts_dir = self.repo_path / "artifacts"
        if not artifacts_dir.is_dir():
            return

        type_mapping = {
            "adr": ArtifactType.ADR,
            "api_spec": ArtifactType.API_SPEC,
            "audit_dossier": ArtifactType.AUDIT_DOSSIER,
            "code_patch": ArtifactType.CODE_PATCH,
            "documentation": ArtifactType.DOCUMENTATION,
            "domain_validation": ArtifactType.DOMAIN_VALIDATION,
            "prd": ArtifactType.PRD,
            "schema_sql": ArtifactType.SCHEMA_SQL,
            "security_audit": ArtifactType.SECURITY_AUDIT,
            "test_report": ArtifactType.TEST_REPORT,
        }

        creator_mapping = {
            ArtifactType.PRD: "ProductManagerAgent",
            ArtifactType.ADR: "SystemArchitectAgent",
            ArtifactType.API_SPEC: "TechLeadAgent",
            ArtifactType.SCHEMA_SQL: "DatabaseArchitectAgent",
            ArtifactType.CODE_PATCH: "BackendEngineerAgent",
            ArtifactType.DOCUMENTATION: "TechnicalWriterAgent",
            ArtifactType.AUDIT_DOSSIER: "CodeReviewerAgent",
            ArtifactType.SECURITY_AUDIT: "AppSecAgent",
            ArtifactType.TEST_REPORT: "QASDETAgent",
            ArtifactType.DOMAIN_VALIDATION: "DomainSMEAgent",
        }

        for sub_dir in artifacts_dir.iterdir():
            if not sub_dir.is_dir():
                continue
            folder_name = sub_dir.name.lower()
            art_type = type_mapping.get(folder_name, ArtifactType.DOCUMENTATION)

            for file_path in sub_dir.glob("*"):
                if not file_path.is_file():
                    continue
                name = file_path.name
                clean_id = f"art-{name.replace('.', '-')}"
                if clean_id in self._artifacts:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                rel_path = f"artifacts/{folder_name}/{name}"
                creator = creator_mapping.get(art_type, "MAS Engine")
                if "react" in name.lower() or name.endswith((".tsx", ".jsx")):
                    creator = "FrontendEngineerAgent"
                elif name.endswith(".tf"):
                    creator = "CloudEngineerAgent"
                elif "dockerfile" in name.lower():
                    creator = "DevOpsSREAgent"

                self._artifacts[clean_id] = Artifact(
                    id=clean_id,
                    type=art_type,
                    name=name,
                    path=rel_path,
                    content=content,
                    version=1,
                    created_by=creator,
                )

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        # 1. Exact ID match
        if artifact_id in self._artifacts:
            return self._artifacts[artifact_id]

        # 2. Match by filename, relative path, or case-insensitive ID
        for art in self._artifacts.values():
            if art.name == artifact_id or art.path == artifact_id:
                return art
            if art.id.lower() == artifact_id.lower() or art.name.lower() == artifact_id.lower():
                return art

        # 3. Dynamic disk fallback: find matching file in artifacts/
        artifacts_dir = self.repo_path / "artifacts"
        if artifacts_dir.is_dir():
            for f in artifacts_dir.glob("**/*"):
                if f.is_file():
                    if (
                        f.name == artifact_id
                        or f.name.lower() == artifact_id.lower()
                        or f"art-{f.name.replace('.', '-')}".lower() == artifact_id.lower()
                        or str(f.relative_to(self.repo_path)).replace("\\", "/") == artifact_id
                    ):
                        try:
                            content = f.read_text(encoding="utf-8", errors="replace")
                            clean_id = f"art-{f.name.replace('.', '-')}"
                            art = Artifact(
                                id=clean_id,
                                type=ArtifactType.DOCUMENTATION,
                                name=f.name,
                                path=str(f.relative_to(self.repo_path)).replace("\\", "/"),
                                content=content,
                                version=1,
                                created_by="MAS Engine",
                                version_history=[{
                                    "version": 1,
                                    "content": content,
                                    "created_by": "MAS Engine",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }],
                            )
                            self._artifacts[clean_id] = art
                            return art
                        except Exception:
                            pass

        return None

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
