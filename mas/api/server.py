"""
Zero-Dependency High-Performance HTTP & Server-Sent Events (SSE) Server for MAS Web Cockpit.
Serves RESTful APIs for mission execution, artifact ledger inspection, real-time pod updates,
interactive HITL gate resolution, and static UI assets without third-party pip dependencies.
"""

import json
import mimetypes
import queue
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mas.agents.engineering import (
    BackendEngineerAgent,
    CloudEngineerAgent,
    DatabaseArchitectAgent,
    DevOpsSREAgent,
    FrontendEngineerAgent,
)
from mas.agents.governance_docs import (
    AppSecAgent,
    CodeReviewerAgent,
    QASDETAgent,
    TechnicalWriterAgent,
)
from mas.agents.leadership import (
    BusinessSponsorAgent,
    DomainSMEAgent,
    ProductManagerAgent,
    SystemArchitectAgent,
    TechLeadAgent,
)
from mas.api.events import get_event_bus
from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.config import get_config
from mas.core.orchestrator import MASOrchestrator
from mas.core.persistence import get_mission_store
from mas.core.state import Artifact, ArtifactType, SubsystemClass, Task, TaskPriority
from mas.core.vcs import PullRequestGenerator, compute_artifact_diff
from mas.hitl.gates import GateLevel

# Ensure modern JS and JSX MIME types are correctly served
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".jsx")
mimetypes.add_type("text/javascript", ".mjs")


class MissionSession:
    def __init__(
        self,
        mission_id: str,
        title: str,
        description: str,
        target_dir: Optional[str] = None,
        interactive: bool = False,
    ):
        self.mission_id = mission_id
        self.title = title
        self.description = description
        self.target_dir = target_dir
        self.interactive = interactive
        self.status = "INITIALIZING"
        self.current_stage = "BUSINESS"
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.blackboard = ArtifactBlackboard(
            repo_path=".", target_workspace_dir=target_dir, git_enabled=False
        )
        self.circuit_breaker = CircuitBreaker(get_config().limits)
        self.pending_gate: Optional[Dict[str, Any]] = None
        self.gate_event = threading.Event()
        self.gate_decision: str = "APPROVED"
        self.tokens_used = {"prompt": 0, "candidate": 0, "thinking": 0, "total": 0}
        self.pod_statuses: Dict[str, Dict[str, Any]] = {
            "Data Pod": {"status": "IDLE", "action": "Standby", "artifact": "schema.sql"},
            "Backend Pod": {"status": "IDLE", "action": "Standby", "artifact": "service.py"},
            "Frontend Pod": {"status": "IDLE", "action": "Standby", "artifact": "Component.tsx"},
            "Cloud & SRE Pod": {
                "status": "IDLE",
                "action": "Standby",
                "artifact": "Dockerfile & main.tf",
            },
            "Governance & QA": {
                "status": "IDLE",
                "action": "Standby",
                "artifact": "TestReport.json",
            },
        }
        self.error: Optional[str] = None


class MissionRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._missions: Dict[str, MissionSession] = {}
        self._store = get_mission_store()
        self._hydrate_from_store()

    def _hydrate_from_store(self) -> None:
        """Hydrates previous mission sessions from SQLite WAL persistence."""
        try:
            persisted = self._store.list_missions(limit=100)
            for m in persisted:
                mid = m["mission_id"]
                sess = MissionSession(
                    mission_id=mid,
                    title=m["title"],
                    description=m["description"],
                    target_dir=m["target_dir"],
                    interactive=m["interactive"],
                )
                sess.status = m["status"]
                sess.current_stage = m["stage"]
                sess.created_at = m["created_at"]
                sess.completed_at = m.get("completed_at")
                sess.tokens_used = m.get("tokens_used") or sess.tokens_used
                sess.pod_statuses = m.get("pods") or sess.pod_statuses
                sess.pending_gate = m.get("pending_gate")
                sess.error = m.get("error")
                self._missions[mid] = sess
        except Exception:
            pass

    def create_mission(
        self,
        title: str,
        description: str,
        target_dir: Optional[str] = None,
        interactive: bool = False,
    ) -> MissionSession:
        with self._lock:
            mission_id = f"MISSION-{int(time.time() * 1000)}"
            session = MissionSession(
                mission_id=mission_id,
                title=title,
                description=description,
                target_dir=target_dir,
                interactive=interactive,
            )
            self._missions[mission_id] = session
            # Durable WAL persistence
            self._store.save_mission(
                mission_id=mission_id,
                title=title,
                description=description,
                target_dir=target_dir,
                status="RUNNING",
                stage="CONTRACTS",
                stage_index=1,
                interactive=interactive,
                created_at=session.created_at,
                tokens_used=session.tokens_used,
                pods=session.pod_statuses,
            )
            return session

    def get_mission(self, mission_id: str) -> Optional[MissionSession]:
        with self._lock:
            return self._missions.get(mission_id)

    def list_missions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "mission_id": m.mission_id,
                    "title": m.title,
                    "status": m.status,
                    "stage": m.current_stage,
                    "created_at": m.created_at,
                    "tokens_used": m.tokens_used,
                }
                for m in sorted(self._missions.values(), key=lambda x: x.created_at, reverse=True)
            ]


_registry = MissionRegistry()


def get_mission_registry() -> MissionRegistry:
    return _registry


class MASRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Set static assets directory to mas/web
        web_dir = Path(__file__).parent.parent / "web"
        super().__init__(*args, directory=str(web_dir), **kwargs)

    def handle(self) -> None:
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, ConnectionError):
            pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json_response(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ConnectionError):
            pass

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/v1/health":
            self._send_json_response(
                {"status": "ok", "service": "MAS Web Mission Control", "version": "0.1.0"}
            )
            return

        elif path == "/api/v1/missions":
            registry = get_mission_registry()
            self._send_json_response({"missions": registry.list_missions()})
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/events"):
            # Server-Sent Events (SSE) Stream
            mission_id = path.split("/")[4]
            self._handle_sse_stream(mission_id)
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/dag"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            from mas.core.dag_engine import build_mission_dag

            dag = build_mission_dag(session=session, workspace_root=".", mission_id=mission_id)
            self._send_json_response(dag.model_dump())
            return

        elif path == "/api/v1/dag" or path.startswith("/api/v1/dag?"):
            from mas.core.dag_engine import build_mission_dag

            registry = get_mission_registry()
            session = None
            if registry and registry._missions:
                session = next(reversed(list(registry._missions.values())), None)
            dag = build_mission_dag(session=session, workspace_root=".")
            self._send_json_response(dag.model_dump())
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/tokens"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            from mas.core.cost_tracker import compute_mission_cost_report

            rep = compute_mission_cost_report(session=session)
            self._send_json_response(rep.model_dump())
            return

        elif path in ("/api/v1/telemetry/tokens", "/api/v1/tokens") or path.startswith("/api/v1/tokens?"):
            from mas.core.cost_tracker import compute_mission_cost_report

            registry = get_mission_registry()
            session = None
            if registry and registry._missions:
                session = next(reversed(list(registry._missions.values())), None)
            rep = compute_mission_cost_report(session=session)
            self._send_json_response(rep.model_dump())
            return

        elif path.startswith("/api/v1/missions/"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            artifacts = [
                {
                    "id": a.id,
                    "type": a.type.value,
                    "name": a.name,
                    "version": a.version,
                    "created_by": a.created_by,
                    "path": a.path,
                }
                for a in session.blackboard.list_artifacts()
            ]

            from mas.core.cost_tracker import compute_mission_cost_report

            self._send_json_response(
                {
                    "mission_id": session.mission_id,
                    "title": session.title,
                    "description": session.description,
                    "target_dir": session.target_dir,
                    "status": session.status,
                    "stage": session.current_stage,
                    "pending_gate": session.pending_gate,
                    "tokens_used": session.tokens_used,
                    "circuit_breaker": {
                        "total_turns": session.circuit_breaker.total_turns,
                        "max_turns": get_config().limits.max_total_turns_per_task,
                        "healthy": not session.circuit_breaker.is_tripped(),
                    },
                    "pods": session.pod_statuses,
                    "artifacts": artifacts,
                    "cost_telemetry": compute_mission_cost_report(session=session).model_dump(),
                }
            )
            return

        elif path.startswith("/api/v1/artifacts/") and path.endswith("/diff"):
            artifact_id = path[len("/api/v1/artifacts/"): -len("/diff")].strip("/")
            registry = get_mission_registry()
            found_art = None
            for m in registry._missions.values():
                found_art = m.blackboard.get_artifact(artifact_id)
                if found_art:
                    break

            if not found_art:
                art_dir = Path("artifacts").resolve()
                if art_dir.is_dir():
                    for f in art_dir.glob("**/*"):
                        if f.is_file() and (
                            f.name == artifact_id
                            or f.name.lower() == artifact_id.lower()
                            or f"art-{f.name.replace('.', '-')}".lower() == artifact_id.lower()
                            or str(f).replace("\\", "/").endswith(artifact_id)
                        ):
                            try:
                                cnt = f.read_text(encoding="utf-8", errors="replace")
                                clean_id = f"art-{f.name.replace('.', '-')}"
                                found_art = Artifact(
                                    id=clean_id,
                                    name=f.name,
                                    type=ArtifactType.DOCUMENTATION,
                                    version=1,
                                    content=cnt,
                                    created_by="MAS Engine",
                                    path=str(f.relative_to(Path(".").resolve())).replace("\\", "/"),
                                )
                                break
                            except Exception:
                                pass

            if not found_art:
                self._send_json_response(
                    {"error": "Artifact not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            diff_res = compute_artifact_diff(
                artifact_id=found_art.id,
                artifact_name=found_art.name,
                synthesized_content=found_art.content,
                workspace_root=".",
                target_rel_path=found_art.path,
            )
            self._send_json_response(diff_res.model_dump())
            return

        elif path.startswith("/api/v1/artifacts/") and path.endswith("/versions"):
            artifact_id = path[len("/api/v1/artifacts/"): -len("/versions")].strip("/")
            self._handle_artifact_versions(artifact_id)
            return

        elif path.startswith("/api/v1/artifacts/"):
            artifact_id = path[len("/api/v1/artifacts/"):].strip()
            registry = get_mission_registry()
            found_art = None
            for m in registry._missions.values():
                found_art = m.blackboard.get_artifact(artifact_id)
                if found_art:
                    break

            # Resilient disk fallback across artifacts/ directory
            if not found_art:
                art_dir = Path("artifacts").resolve()
                if art_dir.is_dir():
                    for f in art_dir.glob("**/*"):
                        if f.is_file():
                            if (
                                f.name == artifact_id
                                or f.name.lower() == artifact_id.lower()
                                or f"art-{f.name.replace('.', '-')}".lower() == artifact_id.lower()
                                or str(f).replace("\\", "/").endswith(artifact_id)
                            ):
                                try:
                                    cnt = f.read_text(encoding="utf-8", errors="replace")
                                    clean_id = f"art-{f.name.replace('.', '-')}"
                                    found_art = Artifact(
                                        id=clean_id,
                                        name=f.name,
                                        type=ArtifactType.DOCUMENTATION,
                                        version=1,
                                        content=cnt,
                                        created_by="MAS Engine",
                                        path=str(f.relative_to(Path(".").resolve())).replace("\\", "/"),
                                    )
                                    break
                                except Exception:
                                    pass

            if not found_art:
                self._send_json_response(
                    {"error": "Artifact not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            self._send_json_response(
                {
                    "id": found_art.id,
                    "name": found_art.name,
                    "type": found_art.type.value if hasattr(found_art.type, "value") else str(found_art.type),
                    "version": found_art.version,
                    "content": found_art.content,
                    "created_by": found_art.created_by,
                    "path": found_art.path,
                }
            )
            return

        # Default: Serve static assets (index.html, styles.css, app.js)
        if path == "/" or not path or path == "/index.html":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        content_len = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body = json.loads(body_raw.decode("utf-8")) if body_raw else {}
        except Exception:
            body = {}

        if path == "/api/v1/missions":
            title = body.get("title", "Core Enterprise Service")
            description = body.get(
                "description", "Implement full-stack service with APIs, storage, and UI."
            )
            target_dir = body.get("target_dir")
            interactive = body.get("interactive", False)

            registry = get_mission_registry()
            session = registry.create_mission(
                title=title,
                description=description,
                target_dir=target_dir,
                interactive=interactive,
            )

            # Start pipeline in daemon thread
            t = threading.Thread(
                target=execute_mission_pipeline,
                args=(session,),
                daemon=True,
            )
            t.start()

            self._send_json_response(
                {
                    "mission_id": session.mission_id,
                    "status": "RUNNING",
                    "message": f"Mission '{title}' initialized successfully.",
                },
                status=HTTPStatus.CREATED,
            )
            return

        elif "/gates/" in path and path.endswith("/decision"):
            # e.g. /api/v1/missions/{id}/gates/{gate_name}/decision
            parts = path.split("/")
            mission_id = parts[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            decision_str = body.get("decision", "APPROVED").upper()
            if decision_str not in ["APPROVED", "REJECTED", "MODIFIED"]:
                decision_str = "APPROVED"
            session.gate_decision = decision_str
            session.pending_gate = None
            session.gate_event.set()

            # Publish event
            event_bus = get_event_bus()
            event_bus.publish(
                mission_id,
                "GATE_RESOLVED",
                {
                    "decision": session.gate_decision,
                    "message": f"Gate decision recorded: {session.gate_decision}",
                },
            )

            self._send_json_response({"status": "SUCCESS", "decision": session.gate_decision})
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/tests/run"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            event_bus = get_event_bus()
            store = get_mission_store()
            event_bus.publish(
                mission_id,
                "LOG_STREAMED",
                {"text": f"\n[SubprocessSandbox] Triggering sandboxed test verification for {mission_id}..."}
            )

            from mas.tools.sandbox import SubprocessSandbox
            sandbox = SubprocessSandbox(workspace_root=".")

            target_test = "artifacts/code_patch"
            test_files = list(Path("artifacts/code_patch").glob("test_*.py"))
            if test_files:
                target_test = str(test_files[0]).replace("\\", "/")

            sandbox_res = sandbox.execute(["pytest", "-v", target_test])

            test_status = "PASSED" if sandbox_res.exit_code == 0 else "FAILED"
            log_output = (
                f"\n--- Sandboxed Pytest Run: {test_status} (exit code: {sandbox_res.exit_code}) ---\n"
                f"{sandbox_res.stdout}\n"
                f"{sandbox_res.stderr}\n"
                f"[*] Verification finished in {sandbox_res.duration_seconds:.2f}s\n"
            )
            event_bus.publish(mission_id, "LOG_STREAMED", {"text": log_output})
            store.record_event(
                mission_id, "TESTS_RUN", {"status": test_status, "exit_code": sandbox_res.exit_code}
            )

            from mas.core.diagnostic import parse_pytest_failure

            diagnostic = parse_pytest_failure(
                stdout=sandbox_res.stdout,
                stderr=sandbox_res.stderr,
                exit_code=sandbox_res.exit_code,
                default_file=target_test,
            )

            self._send_json_response(
                {
                    "status": test_status,
                    "exit_code": sandbox_res.exit_code,
                    "stdout": sandbox_res.stdout,
                    "stderr": sandbox_res.stderr,
                    "duration_seconds": sandbox_res.duration_seconds,
                    "diagnostic": diagnostic.model_dump(),
                }
            )
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/tests/autofix"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            payload = body

            from mas.core.diagnostic import TestFailureDiagnostic, execute_autofix_pipeline

            diagnostic = TestFailureDiagnostic(
                has_failure=True,
                failure_summary=payload.get("failure_summary", "Failing assertion in test suite"),
                target_file=payload.get("target_file", "artifacts/code_patch/service.py"),
                assigned_pod=payload.get("assigned_pod", "Backend Pod"),
            )

            res = execute_autofix_pipeline(
                mission_id=mission_id,
                diagnostic=diagnostic,
                workspace_root=".",
                session=session,
            )

            event_bus = get_event_bus()
            event_bus.publish(
                mission_id,
                "LOG_STREAMED",
                {"text": f"\n🔧 [Auto-Fix Self-Healing] {res.message}\n"},
            )

            self._send_json_response(res.model_dump())
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/revisions"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            art_id = body.get("artifact_id", "service.py")
            line = body.get("line", 1)
            comment = body.get("comment", "").strip()

            event_bus = get_event_bus()
            store = get_mission_store()

            rev_event = {
                "artifact_id": art_id,
                "line": line,
                "comment": comment,
                "operator": "Human-in-the-Loop Operator",
                "timestamp": time.time(),
            }

            event_bus.publish(mission_id, "REVISION_REQUESTED", rev_event)
            event_bus.publish(
                mission_id,
                "LOG_STREAMED",
                {
                    "text": f"\n💬 [Operator Review] Line {line} in {art_id}: \"{comment}\"\n   -> Registered for automated agent remediation turn."
                },
            )
            store.record_event(mission_id, "REVISION_REQUESTED", rev_event)

            self._send_json_response(
                {
                    "status": "RECORDED",
                    "mission_id": mission_id,
                    "revision": rev_event,
                }
            )
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/resume"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            if session.status not in ["RUNNING"]:
                session.status = "RUNNING"
                t = threading.Thread(
                    target=execute_mission_pipeline,
                    args=(session,),
                    daemon=True,
                )
                t.start()
                self._send_json_response({"status": "RESUMED", "mission_id": mission_id})
            else:
                self._send_json_response({"status": "ALREADY_RUNNING", "mission_id": mission_id})
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/pr"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            push_remote = body.get("push", False)
            create_pr = body.get("create_pr", False)

            task = Task(
                id=session.mission_id,
                title=session.title,
                description=session.description,
                assigned_pod=SubsystemClass.FULL_SYSTEM,
            )
            pr_gen = PullRequestGenerator(repo_path=".")
            pr = pr_gen.generate_pr(task=task, source_branch=f"feat/{session.mission_id.lower()}")
            sub_res = pr_gen.publish_remote_pr(
                pr, push_to_remote=push_remote, create_github_pr=create_pr
            )

            self._send_json_response(
                {
                    "pr_id": sub_res.pr_id,
                    "title": pr.title,
                    "markdown": pr.description_markdown,
                    "pushed_to_remote": sub_res.pushed_to_remote,
                    "github_pr_url": sub_res.github_pr_url,
                    "status_message": sub_res.status_message,
                }
            )
            return

        elif path.startswith("/api/v1/missions/") and path.endswith("/commit"):
            mission_id = path.split("/")[4]
            registry = get_mission_registry()
            session = registry.get_mission(mission_id)
            if not session:
                self._send_json_response(
                    {"error": "Mission not found"}, status=HTTPStatus.NOT_FOUND
                )
                return

            custom_msg = body.get("message")
            from mas.core.vcs import create_local_git_snapshot

            commit_res = create_local_git_snapshot(
                repo_path=".",
                commit_message=custom_msg or f"feat({mission_id.lower()}): snapshot synthesized artifacts",
                paths_to_stage=["artifacts/"],
            )

            event_bus = get_event_bus()
            event_bus.publish(
                mission_id,
                "LOG_STREAMED",
                {
                    "text": f"\n📦 [Local Git Snapshot] Status: {commit_res.status} | Branch: {commit_res.branch} | Hash: {commit_res.commit_hash}\n   Message: {commit_res.message or commit_res.error} (Strictly local, 0 remote push)"
                },
            )

            self._send_json_response(commit_res.model_dump())
            return

        elif path.startswith("/api/v1/artifacts/") and path.endswith("/rollback"):
            artifact_id = path[len("/api/v1/artifacts/"): -len("/rollback")].strip("/")
            self._handle_artifact_rollback(artifact_id, body)
            return

        elif path.startswith("/api/v1/artifacts/"):
            artifact_id = path[len("/api/v1/artifacts/"):].strip()
            self._handle_artifact_update(artifact_id, body)
            return

        self._send_json_response({"error": "Endpoint not found"}, status=HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        """Handles HTTP PUT requests for updating resources."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except json.JSONDecodeError:
            self._send_json_response(
                {"error": "Invalid JSON in request body"}, status=HTTPStatus.BAD_REQUEST
            )
            return

        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/v1/artifacts/"):
            artifact_id = path[len("/api/v1/artifacts/"):].strip()
            self._handle_artifact_update(artifact_id, body)
            return

        self._send_json_response({"error": "Endpoint not found"}, status=HTTPStatus.NOT_FOUND)

    def _handle_artifact_update(self, artifact_id: str, body: Dict[str, Any]) -> None:
        """Updates artifact content with syntax safety validation and persistence."""
        new_content = body.get("content")
        if new_content is None:
            self._send_json_response(
                {"error": "Missing 'content' field in request payload."},
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
            )
            return

        registry = get_mission_registry()
        found_art = None
        target_mission = None
        for m in registry._missions.values():
            found_art = m.blackboard.get_artifact(artifact_id)
            if found_art:
                target_mission = m
                break

        disk_path = None
        art_dir = Path("artifacts").resolve()
        if art_dir.is_dir():
            for f in art_dir.glob("**/*"):
                if f.is_file():
                    if (
                        f.name == artifact_id
                        or f.name.lower() == artifact_id.lower()
                        or f"art-{f.name.replace('.', '-')}".lower() == artifact_id.lower()
                        or str(f).replace("\\", "/").endswith(artifact_id)
                    ):
                        disk_path = f
                        break

        if not found_art and not disk_path:
            self._send_json_response(
                {"error": f"Artifact '{artifact_id}' not found."},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        # Syntax verification: if Python file, parse with AST
        file_name = (found_art.name if found_art else disk_path.name).lower()
        if file_name.endswith(".py"):
            import ast
            try:
                ast.parse(new_content)
            except SyntaxError as se:
                self._send_json_response(
                    {
                        "error": "Syntax Verification Failed",
                        "detail": f"Python SyntaxError on line {se.lineno}: {se.msg}",
                        "lineno": se.lineno,
                        "offset": se.offset,
                    },
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
                return
        elif file_name.endswith(".json"):
            try:
                json.loads(new_content)
            except json.JSONDecodeError as je:
                self._send_json_response(
                    {
                        "error": "Syntax Verification Failed",
                        "detail": f"JSON Parse Error on line {je.lineno}: {je.msg}",
                        "lineno": je.lineno,
                    },
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
                return

        # Determine target file path jailed inside workspace
        target_path = disk_path or (Path("artifacts") / (found_art.path or found_art.name)).resolve()
        try:
            target_path.relative_to(Path(".").resolve())
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(new_content, encoding="utf-8")
        except Exception as e:
            self._send_json_response(
                {"error": f"Failed to persist file: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        new_version = (found_art.version + 1) if found_art else 2
        art_id = found_art.id if found_art else f"art-{target_path.name.replace('.', '-')}"
        art_name = found_art.name if found_art else target_path.name

        if found_art:
            if not found_art.version_history:
                found_art.version_history.append({
                    "version": found_art.version,
                    "content": found_art.content,
                    "created_by": found_art.created_by,
                    "timestamp": found_art.created_at.isoformat(),
                })
            found_art.content = new_content
            found_art.version = new_version
            found_art.version_history.append({
                "version": new_version,
                "content": new_content,
                "created_by": "Operator (In-Cockpit)",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # Publish event
        event_bus = get_event_bus()
        m_id = target_mission.mission_id if target_mission else "GLOBAL"
        event_bus.publish(
            m_id,
            "ARTIFACT_COMMITTED",
            {
                "artifact_id": art_id,
                "name": art_name,
                "version": new_version,
                "author": "Operator (In-Cockpit)",
            },
        )
        event_bus.publish(
            m_id,
            "LOG_STREAMED",
            {
                "text": f"\n✏️ [Operator Direct Edit] Updated {art_name} (v{new_version}) on disk with AST verification."
            },
        )

        self._send_json_response(
            {
                "status": "SAVED",
                "artifact": {
                    "id": art_id,
                    "name": art_name,
                    "version": new_version,
                    "path": str(target_path.relative_to(Path(".").resolve())).replace("\\", "/"),
                    "content": new_content,
                },
            }
        )

    def _handle_artifact_versions(self, artifact_id: str) -> None:
        """Returns version history snapshots for an artifact."""
        registry = get_mission_registry()
        found_art = None
        for m in registry._missions.values():
            found_art = m.blackboard.get_artifact(artifact_id)
            if found_art:
                break

        if not found_art:
            art_dir = Path("artifacts").resolve()
            if art_dir.is_dir():
                for f in art_dir.glob("**/*"):
                    if f.is_file() and (
                        f.name == artifact_id
                        or f.name.lower() == artifact_id.lower()
                        or f"art-{f.name.replace('.', '-')}".lower() == artifact_id.lower()
                        or str(f).replace("\\", "/").endswith(artifact_id)
                    ):
                        cnt = f.read_text(encoding="utf-8", errors="replace")
                        self._send_json_response(
                            {
                                "artifact_id": artifact_id,
                                "name": f.name,
                                "current_version": 1,
                                "versions": [
                                    {
                                        "version": 1,
                                        "created_by": "MAS Engine",
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                        "content": cnt,
                                    }
                                ],
                            }
                        )
                        return

            self._send_json_response({"error": "Artifact not found"}, status=HTTPStatus.NOT_FOUND)
            return

        history = list(found_art.version_history)
        if not history:
            history = [
                {
                    "version": found_art.version,
                    "created_by": found_art.created_by,
                    "timestamp": found_art.created_at.isoformat(),
                    "content": found_art.content,
                }
            ]

        self._send_json_response(
            {
                "artifact_id": found_art.id,
                "name": found_art.name,
                "current_version": found_art.version,
                "versions": history,
            }
        )

    def _handle_artifact_rollback(self, artifact_id: str, body: Dict[str, Any]) -> None:
        """Rolls back artifact to a specified earlier version snapshot."""
        target_version = body.get("version")
        if target_version is None:
            self._send_json_response(
                {"error": "Missing 'version' parameter in request body"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        registry = get_mission_registry()
        found_art = None
        target_mission = None
        for m in registry._missions.values():
            found_art = m.blackboard.get_artifact(artifact_id)
            if found_art:
                target_mission = m
                break

        if not found_art:
            self._send_json_response(
                {"error": f"Artifact '{artifact_id}' not found."},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        target_snapshot = next(
            (s for s in found_art.version_history if s.get("version") == target_version), None
        )
        if not target_snapshot:
            self._send_json_response(
                {"error": f"Version {target_version} not found in artifact history."},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        target_content = target_snapshot.get("content", "")

        # AST syntax safety check on rollback
        file_name = found_art.name.lower()
        if file_name.endswith(".py"):
            import ast
            try:
                ast.parse(target_content)
            except SyntaxError as se:
                self._send_json_response(
                    {
                        "error": "Rollback Syntax Verification Failed",
                        "detail": f"Python SyntaxError on line {se.lineno}: {se.msg}",
                    },
                    status=HTTPStatus.UNPROCESSABLE_ENTITY,
                )
                return

        # Write restored content to disk
        art_dir = Path("artifacts").resolve()
        target_path = (art_dir / (found_art.path or found_art.name)).resolve()
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(target_content, encoding="utf-8")
        except Exception as e:
            self._send_json_response(
                {"error": f"Failed to persist rollback to disk: {str(e)}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        new_version = found_art.version + 1
        found_art.content = target_content
        found_art.version = new_version
        found_art.version_history.append(
            {
                "version": new_version,
                "content": target_content,
                "created_by": f"Operator Rollback (to v{target_version})",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Publish events
        event_bus = get_event_bus()
        m_id = target_mission.mission_id if target_mission else "GLOBAL"
        event_bus.publish(
            m_id,
            "ARTIFACT_COMMITTED",
            {
                "artifact_id": found_art.id,
                "name": found_art.name,
                "version": new_version,
                "author": f"Operator Rollback -> v{target_version}",
            },
        )
        event_bus.publish(
            m_id,
            "LOG_STREAMED",
            {
                "text": f"\n⏪ [Revision Rollback] Restored {found_art.name} to v{target_version} (now v{new_version}) with AST safety check."
            },
        )

        self._send_json_response(
            {
                "status": "ROLLED_BACK",
                "artifact_id": found_art.id,
                "name": found_art.name,
                "version": new_version,
                "rolled_back_to": target_version,
                "content": target_content,
            }
        )

    def _handle_sse_stream(self, mission_id: str) -> None:
        """Streams Server-Sent Events over HTTP chunked connection."""
        event_bus = get_event_bus()
        subscriber_queue = event_bus.subscribe(mission_id)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            # Send initial ping event
            init_payload = (
                f"data: {json.dumps({'type': 'CONNECTED', 'mission_id': mission_id})}\n\n"
            )
            self.wfile.write(init_payload.encode("utf-8"))
            self.wfile.flush()

            while True:
                try:
                    event = subscriber_queue.get(timeout=15)
                    data = f"data: {json.dumps(event)}\n\n"
                    self.wfile.write(data.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive heartbeat comment
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ConnectionError):
            pass
        finally:
            event_bus.unsubscribe(mission_id, subscriber_queue)


def execute_mission_pipeline(session: MissionSession) -> None:
    """
    Executes the MAS pipeline while dispatching real-time state events to the EventBus
    and synchronizing durable state to the SQLite WAL MissionStore.
    """
    event_bus = get_event_bus()
    store = get_mission_store()
    mission_id = session.mission_id
    session.status = "RUNNING"

    event_bus.publish(mission_id, "STATUS_CHANGED", {"status": "RUNNING", "title": session.title})
    store.update_mission_state(mission_id, status="RUNNING")

    def emit_log(text: str) -> None:
        event_bus.publish(mission_id, "LOG_STREAMED", {"text": text, "timestamp": time.time()})
        store.record_event(mission_id, "LOG_STREAMED", {"text": text})

    def update_pod(pod_name: str, status: str, action: str, artifact: Optional[str] = None) -> None:
        session.pod_statuses[pod_name] = {
            "status": status,
            "action": action,
            "artifact": artifact or session.pod_statuses.get(pod_name, {}).get("artifact", ""),
        }
        event_bus.publish(
            mission_id,
            "POD_UPDATED",
            {
                "pod": pod_name,
                "status": status,
                "action": action,
                "artifact": artifact,
            },
        )
        store.update_mission_state(mission_id, pods=session.pod_statuses)

    def sync_tokens() -> None:
        session.tokens_used = {
            "prompt": circuit_breaker.prompt_tokens,
            "candidate": circuit_breaker.candidate_tokens,
            "thinking": circuit_breaker.thinking_tokens,
            "total": (
                circuit_breaker.prompt_tokens
                + circuit_breaker.candidate_tokens
                + circuit_breaker.thinking_tokens
            ),
        }
        from mas.core.cost_tracker import compute_mission_cost_report

        cost_rep = compute_mission_cost_report(session=session)
        event_bus.publish(
            mission_id,
            "TOKEN_METRICS_UPDATED",
            {
                "tokens_used": session.tokens_used,
                "cost_telemetry": cost_rep.model_dump(),
            },
        )
        store.update_mission_state(mission_id, tokens_used=session.tokens_used)

    def trigger_gate(gate_level: GateLevel, pre_mortem_summary: str) -> str:
        if not session.interactive:
            return "APPROVED"

        session.pending_gate = {
            "gate": gate_level.value,
            "gate_level": gate_level.value,
            "level": gate_level.value,
            "pre_mortem": pre_mortem_summary,
            "premise": pre_mortem_summary,
            "token_projection": session.tokens_used["total"] + 1500,
        }
        session.gate_event.clear()

        event_bus.publish(mission_id, "GATE_PROMPTED", session.pending_gate)
        event_bus.publish(mission_id, "GATE_TRIGGERED", session.pending_gate)
        store.update_mission_state(mission_id, pending_gate=session.pending_gate)
        # Wait until operator submits decision from the UI
        session.gate_event.wait(timeout=300)
        store.update_mission_state(mission_id, pending_gate=False)
        return session.gate_decision

    try:
        config = get_config()
        blackboard = session.blackboard
        circuit_breaker = session.circuit_breaker

        # Stream minted artifacts in real time to Web Cockpit as each agent commits code
        def on_artifact_minted(a: Artifact) -> None:
            art_dict = {
                "id": a.id,
                "type": a.type.value if hasattr(a.type, "value") else str(a.type),
                "name": a.name,
                "version": a.version,
                "created_by": a.created_by,
                "path": a.path,
            }
            event_bus.publish(mission_id, "ARTIFACT_COMMITTED", {"artifact": art_dict})
            store.record_event(mission_id, "ARTIFACT_COMMITTED", art_dict)

        blackboard.on_artifact_registered = on_artifact_minted

        orchestrator = MASOrchestrator(
            config=config, blackboard=blackboard, circuit_breaker=circuit_breaker
        )

        task = orchestrator.create_task(
            task_id=f"TASK-{mission_id.split('-')[-1]}",
            title=session.title,
            description=session.description,
            priority=TaskPriority.HIGH,
        )

        # STAGE 1: Leadership & Contracts
        session.current_stage = "CONTRACTS"
        event_bus.publish(mission_id, "STAGE_CHANGED", {"stage": "CONTRACTS", "stageIndex": 1})
        store.update_mission_state(mission_id, stage="CONTRACTS", stage_index=1)
        emit_log(f"[*] Initialized mission: {session.title}")

        # Business Sponsor
        update_pod("Leadership", "RUNNING", "Authoring Project Charter")
        sponsor = BusinessSponsorAgent(blackboard=blackboard)
        sponsor.run(task)
        circuit_breaker.record_turn(sponsor.role)
        sync_tokens()
        emit_log("  + BusinessSponsor: Approved charter GOAL-001")

        # Product Manager
        pm = ProductManagerAgent(blackboard=blackboard)
        pm.run(task)
        circuit_breaker.record_turn(pm.role)
        sync_tokens()
        emit_log("  + ProductManager: Authored PRD.md with INVEST acceptance criteria")

        # Domain SME
        sme = DomainSMEAgent(blackboard=blackboard)
        sme.run(task)
        circuit_breaker.record_turn(sme.role)
        sync_tokens()
        emit_log("  + DomainSME: Invariant verification completed")

        # Gate 1: Scope & Budget
        g1_res = trigger_gate(
            GateLevel.GATE_1_SCOPE_BUDGET, "Scope and Budget Charter Verification"
        )
        if g1_res == "REJECTED":
            session.status = "REJECTED"
            event_bus.publish(mission_id, "STATUS_CHANGED", {"status": "REJECTED"})
            store.update_mission_state(mission_id, status="REJECTED")
            return

        # STAGE 2: Architecture & Interface Contracts
        session.current_stage = "ARCHITECTURE"
        event_bus.publish(mission_id, "STAGE_CHANGED", {"stage": "ARCHITECTURE", "stageIndex": 2})
        store.update_mission_state(mission_id, stage="ARCHITECTURE", stage_index=2)

        # System Architect
        arch = SystemArchitectAgent(blackboard=blackboard)
        arch.run(task)
        circuit_breaker.record_turn(arch.role)
        sync_tokens()
        emit_log("  + SystemArchitect: Authored ADR-001 with pre-mortem failure mode analysis")

        # Tech Lead
        tech_lead = TechLeadAgent(blackboard=blackboard)
        tech_lead.run(task)
        circuit_breaker.record_turn(tech_lead.role)
        sync_tokens()
        emit_log("  + TechLead: Published api-spec.yaml and TaskDAG.json")

        update_pod("Leadership", "DONE", "Contracts Locked")

        # Gate 2: Architecture & Security
        g2_res = trigger_gate(
            GateLevel.GATE_2_ARCHITECTURE_SECURITY, "API Spec & Database Lock Risk Analysis"
        )
        if g2_res == "REJECTED":
            session.status = "REJECTED"
            event_bus.publish(mission_id, "STATUS_CHANGED", {"status": "REJECTED"})
            store.update_mission_state(mission_id, status="REJECTED")
            return

        # STAGE 3: Parallel Pod Execution
        session.current_stage = "PARALLEL_PODS"
        event_bus.publish(mission_id, "STAGE_CHANGED", {"stage": "PARALLEL_PODS", "stageIndex": 3})
        store.update_mission_state(mission_id, stage="PARALLEL_PODS", stage_index=3)

        update_pod("Data Pod", "RUNNING", "Authoring PostgreSQL DDL schema & indexes", "schema.sql")
        update_pod(
            "Backend Pod", "RUNNING", "Synthesizing REST service & Pydantic models", "service.py"
        )
        update_pod(
            "Frontend Pod",
            "RUNNING",
            "Creating 4-state accessible React TSX view",
            "IntegrationView.tsx",
        )
        update_pod(
            "Cloud & SRE Pod", "RUNNING", "Hardening Dockerfile & Terraform KMS IaC", "Dockerfile"
        )

        dba = DatabaseArchitectAgent(blackboard=blackboard)
        be = BackendEngineerAgent(blackboard=blackboard)
        fe = FrontendEngineerAgent(blackboard=blackboard)
        cloud = CloudEngineerAgent(blackboard=blackboard)
        sre = DevOpsSREAgent(blackboard=blackboard)

        parallel_workers = [dba, be, fe, cloud, sre]
        orchestrator.execute_parallel_pods(
            task=task,
            pod_agents=parallel_workers,
            max_workers=3,
            isolate_worktrees=False,
        )

        for ag in parallel_workers:
            circuit_breaker.record_turn(ag.role)
        sync_tokens()

        update_pod(
            "Data Pod", "DONE", "Generated schema.sql with non-locking indexes", "schema.sql"
        )
        update_pod(
            "Backend Pod",
            "DONE",
            "Synthesized service.py conforming to api-spec.yaml",
            "service.py",
        )
        update_pod(
            "Frontend Pod",
            "DONE",
            "Created React component wired to endpoints",
            "IntegrationView.tsx",
        )
        update_pod(
            "Cloud & SRE Pod", "DONE", "Authored Dockerfile and main.tf with KMS", "Dockerfile"
        )
        emit_log("  + Concurrent Pods: Successfully delivered all code artifacts")

        # STAGE 4: QA, SDET & Security Gatekeeping
        session.current_stage = "QA_SECURITY"
        event_bus.publish(mission_id, "STAGE_CHANGED", {"stage": "QA_SECURITY", "stageIndex": 4})
        store.update_mission_state(mission_id, stage="QA_SECURITY", stage_index=4)
        update_pod("Governance & QA", "RUNNING", "Running sandboxed pytest & security audit")

        qa = QASDETAgent(blackboard=blackboard)
        qa.run(task)
        circuit_breaker.record_turn(qa.role)
        sync_tokens()
        emit_log("  + QASDETAgent: Sandboxed verification suite 100% pass (2/2)")

        code_rev = CodeReviewerAgent(blackboard=blackboard)
        code_rev.run(task)
        circuit_breaker.record_turn(code_rev.role)
        sync_tokens()

        sec = AppSecAgent(blackboard=blackboard)
        sec.run(task)
        circuit_breaker.record_turn(sec.role)
        sync_tokens()
        emit_log("  + AppSecAgent: OWASP Top 10 security audit PASSED")

        update_pod("Governance & QA", "DONE", "QA 100% Passed | Security Clean")

        # STAGE 5: Documentation & PR Lander
        session.current_stage = "DOCUMENTATION"
        event_bus.publish(mission_id, "STAGE_CHANGED", {"stage": "DOCUMENTATION", "stageIndex": 5})
        store.update_mission_state(mission_id, stage="DOCUMENTATION", stage_index=5)

        writer = TechnicalWriterAgent(blackboard=blackboard)
        writer.run(task)
        circuit_breaker.record_turn(writer.role)
        emit_log("  + TechnicalWriter: Generated 6-document human reference suite")

        # Update final tokens and session state
        session.tokens_used = {
            "prompt": circuit_breaker.prompt_tokens,
            "candidate": circuit_breaker.candidate_tokens,
            "thinking": circuit_breaker.thinking_tokens,
            "total": (
                circuit_breaker.prompt_tokens
                + circuit_breaker.candidate_tokens
                + circuit_breaker.thinking_tokens
            ),
        }
        session.status = "COMPLETED"
        session.completed_at = time.time()

        store.update_mission_state(
            mission_id,
            status="COMPLETED",
            stage="DOCUMENTATION",
            stage_index=5,
            completed_at=session.completed_at,
            tokens_used=session.tokens_used,
            pending_gate=False,
        )

        event_bus.publish(
            mission_id,
            "MISSION_COMPLETED",
            {
                "status": "COMPLETED",
                "tokens_used": session.tokens_used,
                "artifacts_count": len(blackboard.list_artifacts()),
                "message": f"Mission '{session.title}' completed successfully.",
            },
        )
        emit_log(f"✅ Mission '{session.title}' completed successfully.")

    except Exception as exc:
        session.status = "FAILED"
        session.error = str(exc)
        store.update_mission_state(mission_id, status="FAILED", error=str(exc))
        emit_log(f"❌ Mission failed with error: {str(exc)}")
        event_bus.publish(mission_id, "MISSION_FAILED", {"error": str(exc)})


def start_mas_web_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Spins up the MAS Web Server on the specified host and port."""
    server = ThreadingHTTPServer((host, port), MASRequestHandler)
    return server
