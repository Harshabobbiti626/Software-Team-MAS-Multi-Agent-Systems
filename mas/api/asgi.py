"""
High-Performance FastAPI ASGI Engine for MAS Multi-Agent Operating System.
Provides OpenAPI /docs documentation, async endpoints, WebSocket/SSE streaming,
and production-ready ASGI deployment support with Uvicorn/Gunicorn.
"""

import json
import queue
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mas.api.events import get_event_bus
from mas.api.server import execute_mission_pipeline, get_mission_registry
from mas.core.config import get_config
from mas.core.cost_tracker import compute_mission_cost_report
from mas.core.persistence import get_mission_store
from mas.core.state import Artifact, ArtifactType
from mas.core.vcs import PullRequestGenerator, compute_artifact_diff

app = FastAPI(
    title="MAS Multi-Agent Operating System API",
    description="Enterprise-grade deterministic multi-agent software engineering API with contract-first parallel pods.",
    version="0.2.0",
)

# Enable CORS for cross-origin IDE integration and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Web directory
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


# Pydantic Request Models
class CreateMissionRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    target_dir: Optional[str] = None
    interactive: bool = False
    git_commit: bool = False


class GateDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED|MODIFIED)$")
    feedback: Optional[str] = ""


class PullRequestAPIRequest(BaseModel):
    push: bool = False
    create_pr: bool = False


class RevisionRequest(BaseModel):
    artifact_id: str = "service.py"
    line: int = 1
    comment: str = Field(..., min_length=1)


class UpdateArtifactRequest(BaseModel):
    content: str = Field(..., description="Full updated content of the artifact.")


class CommitAPIRequest(BaseModel):
    message: Optional[str] = None


class RollbackArtifactRequest(BaseModel):
    version: int = Field(..., description="Target version number to rollback to.")


class AutoFixAPIRequest(BaseModel):
    failure_summary: Optional[str] = None
    target_file: Optional[str] = None
    assigned_pod: Optional[str] = None


# --- REST API Endpoints ---


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": "MAS Web Mission Control (FastAPI ASGI)",
        "version": "0.2.0",
        "runtime": "asgi_uvicorn",
    }


@app.get("/api/v1/missions")
async def list_missions():
    registry = get_mission_registry()
    return {"missions": registry.list_missions()}


@app.post("/api/v1/missions", status_code=status.HTTP_201_CREATED)
async def create_mission(req: CreateMissionRequest):
    import threading

    registry = get_mission_registry()
    session = registry.create_mission(
        title=req.title,
        description=req.description,
        target_dir=req.target_dir,
        interactive=req.interactive,
    )

    t = threading.Thread(
        target=execute_mission_pipeline, args=(session,), daemon=True
    )
    t.start()

    return {
        "mission_id": session.mission_id,
        "status": "PENDING",
        "message": f"Mission '{req.title}' initialized successfully.",
    }


@app.get("/api/v1/missions/{mission_id}")
async def get_mission_details(mission_id: str):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    artifacts = [
        {
            "id": a.id,
            "type": a.type.value if hasattr(a.type, "value") else str(a.type),
            "name": a.name,
            "version": a.version,
            "created_by": a.created_by,
            "path": a.path,
        }
        for a in session.blackboard.list_artifacts()
    ]

    return {
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


@app.get("/api/v1/telemetry/tokens")
@app.get("/api/v1/tokens")
async def get_tokens_telemetry():
    from mas.core.cost_tracker import compute_mission_cost_report

    registry = get_mission_registry()
    session = None
    if registry and registry._missions:
        session = next(reversed(list(registry._missions.values())), None)
    rep = compute_mission_cost_report(session=session)
    return rep.model_dump()


@app.get("/api/v1/missions/{mission_id}/tokens")
async def get_mission_tokens_telemetry(mission_id: str):
    from mas.core.cost_tracker import compute_mission_cost_report

    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    rep = compute_mission_cost_report(session=session)
    return rep.model_dump()


@app.get("/api/v1/dag")
async def get_global_dag():
    from mas.core.dag_engine import build_mission_dag

    registry = get_mission_registry()
    session = None
    if registry and registry._missions:
        session = next(reversed(list(registry._missions.values())), None)
    dag = build_mission_dag(session=session, workspace_root=".")
    return dag.model_dump()


@app.get("/api/v1/missions/{mission_id}/dag")
async def get_mission_dag_endpoint(mission_id: str):
    from mas.core.dag_engine import build_mission_dag

    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    dag = build_mission_dag(session=session, workspace_root=".", mission_id=mission_id)
    return dag.model_dump()


@app.get("/api/v1/missions/{mission_id}/events")
async def sse_event_stream(mission_id: str):
    event_bus = get_event_bus()
    subscriber_queue = event_bus.subscribe(mission_id)

    async def event_generator():
        # Initial ping
        yield f"data: {json.dumps({'type': 'CONNECTED', 'mission_id': mission_id})}\n\n"
        try:
            while True:
                try:
                    event = subscriber_queue.get(timeout=15)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            event_bus.unsubscribe(mission_id, subscriber_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.post("/api/v1/missions/{mission_id}/gates/{gate_name}/decision")
async def submit_gate_decision(
    mission_id: str, gate_name: str, req: GateDecisionRequest
):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    session.gate_decision = req.decision
    session.pending_gate = None
    session.gate_event.set()

    event_bus = get_event_bus()
    event_bus.publish(
        mission_id,
        "GATE_RESOLVED",
        {"gate": gate_name, "decision": req.decision, "feedback": req.feedback},
    )

    store = get_mission_store()
    store.update_mission_state(mission_id, pending_gate=False)

    return {
        "status": "ok",
        "gate": gate_name,
        "decision": req.decision,
        "feedback": req.feedback,
    }


@app.post("/api/v1/missions/{mission_id}/tests/run")
async def run_sandboxed_tests(mission_id: str):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    event_bus = get_event_bus()
    store = get_mission_store()
    event_bus.publish(
        mission_id,
        "LOG_STREAMED",
        {"text": f"\n[SubprocessSandbox] Triggering sandboxed test verification for {mission_id}..."},
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

    return {
        "status": test_status,
        "exit_code": sandbox_res.exit_code,
        "stdout": sandbox_res.stdout,
        "stderr": sandbox_res.stderr,
        "duration_seconds": sandbox_res.duration_seconds,
        "diagnostic": diagnostic.model_dump(),
    }


@app.post("/api/v1/missions/{mission_id}/tests/autofix")
async def autofix_sandboxed_test_failure(
    mission_id: str, req: AutoFixAPIRequest = AutoFixAPIRequest()
):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    from mas.core.diagnostic import TestFailureDiagnostic, execute_autofix_pipeline

    diagnostic = TestFailureDiagnostic(
        has_failure=True,
        failure_summary=req.failure_summary or "Failing assertion in test suite",
        target_file=req.target_file or "artifacts/code_patch/service.py",
        assigned_pod=req.assigned_pod or "Backend Pod",
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

    return res.model_dump()


@app.post("/api/v1/missions/{mission_id}/revisions")
async def request_code_revision(mission_id: str, req: RevisionRequest):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    event_bus = get_event_bus()
    store = get_mission_store()

    rev_event = {
        "artifact_id": req.artifact_id,
        "line": req.line,
        "comment": req.comment,
        "operator": "Human-in-the-Loop Operator",
        "timestamp": time.time(),
    }

    event_bus.publish(mission_id, "REVISION_REQUESTED", rev_event)
    event_bus.publish(
        mission_id,
        "LOG_STREAMED",
        {
            "text": f"\n💬 [Operator Review] Line {req.line} in {req.artifact_id}: \"{req.comment}\"\n   -> Registered for automated agent remediation turn."
        },
    )
    store.record_event(mission_id, "REVISION_REQUESTED", rev_event)

    return {
        "status": "RECORDED",
        "mission_id": mission_id,
        "revision": rev_event,
    }


@app.get("/api/v1/artifacts/{artifact_id}/diff")
async def get_artifact_diff(artifact_id: str):
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
        raise HTTPException(status_code=404, detail="Artifact not found")

    diff_res = compute_artifact_diff(
        artifact_id=found_art.id,
        artifact_name=found_art.name,
        synthesized_content=found_art.content,
        workspace_root=".",
        target_rel_path=found_art.path,
    )
    return diff_res.model_dump()


@app.get("/api/v1/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
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
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {
        "id": found_art.id,
        "name": found_art.name,
        "type": found_art.type.value if hasattr(found_art.type, "value") else str(found_art.type),
        "version": found_art.version,
        "content": found_art.content,
        "created_by": found_art.created_by,
        "path": found_art.path,
    }


@app.put("/api/v1/artifacts/{artifact_id}")
@app.post("/api/v1/artifacts/{artifact_id}")
async def update_artifact(artifact_id: str, req: UpdateArtifactRequest):
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
            if f.is_file() and (
                f.name == artifact_id
                or f.name.lower() == artifact_id.lower()
                or f"art-{f.name.replace('.', '-')}".lower() == artifact_id.lower()
                or str(f).replace("\\", "/").endswith(artifact_id)
            ):
                disk_path = f
                break

    if not found_art and not disk_path:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    file_name = (found_art.name if found_art else disk_path.name).lower()
    if file_name.endswith(".py"):
        import ast

        try:
            ast.parse(req.content)
        except SyntaxError as se:
            raise HTTPException(
                status_code=422,
                detail=f"Python SyntaxError on line {se.lineno}: {se.msg}",
            )
    elif file_name.endswith(".json"):
        try:
            json.loads(req.content)
        except json.JSONDecodeError as je:
            raise HTTPException(
                status_code=422,
                detail=f"JSON Parse Error on line {je.lineno}: {je.msg}",
            )

    target_path = disk_path or (Path("artifacts") / (found_art.path or found_art.name)).resolve()
    try:
        target_path.relative_to(Path(".").resolve())
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(req.content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist file: {str(e)}")

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
        found_art.content = req.content
        found_art.version = new_version
        found_art.version_history.append({
            "version": new_version,
            "content": req.content,
            "created_by": "Operator (In-Cockpit)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

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

    return {
        "status": "SAVED",
        "artifact": {
            "id": art_id,
            "name": art_name,
            "version": new_version,
            "path": str(target_path.relative_to(Path(".").resolve())).replace("\\", "/"),
            "content": req.content,
        },
    }


@app.get("/api/v1/artifacts/{artifact_id}/versions")
async def get_artifact_versions(artifact_id: str):
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
                    return {
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

        raise HTTPException(status_code=404, detail="Artifact not found")

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

    return {
        "artifact_id": found_art.id,
        "name": found_art.name,
        "current_version": found_art.version,
        "versions": history,
    }


@app.post("/api/v1/artifacts/{artifact_id}/rollback")
async def rollback_artifact(artifact_id: str, req: RollbackArtifactRequest):
    registry = get_mission_registry()
    found_art = None
    target_mission = None
    for m in registry._missions.values():
        found_art = m.blackboard.get_artifact(artifact_id)
        if found_art:
            target_mission = m
            break

    if not found_art:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    target_snapshot = next(
        (s for s in found_art.version_history if s.get("version") == req.version), None
    )
    if not target_snapshot:
        raise HTTPException(
            status_code=404, detail=f"Version {req.version} not found in artifact history"
        )

    target_content = target_snapshot.get("content", "")

    file_name = found_art.name.lower()
    if file_name.endswith(".py"):
        import ast
        try:
            ast.parse(target_content)
        except SyntaxError as se:
            raise HTTPException(
                status_code=422,
                detail=f"Rollback Python SyntaxError on line {se.lineno}: {se.msg}",
            )

    art_dir = Path("artifacts").resolve()
    target_path = (art_dir / (found_art.path or found_art.name)).resolve()
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(target_content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist rollback to disk: {str(e)}")

    new_version = found_art.version + 1
    found_art.content = target_content
    found_art.version = new_version
    found_art.version_history.append(
        {
            "version": new_version,
            "content": target_content,
            "created_by": f"Operator Rollback (to v{req.version})",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    event_bus = get_event_bus()
    m_id = target_mission.mission_id if target_mission else "GLOBAL"
    event_bus.publish(
        m_id,
        "ARTIFACT_COMMITTED",
        {
            "artifact_id": found_art.id,
            "name": found_art.name,
            "version": new_version,
            "author": f"Operator Rollback -> v{req.version}",
        },
    )
    event_bus.publish(
        m_id,
        "LOG_STREAMED",
        {
            "text": f"\n⏪ [Revision Rollback] Restored {found_art.name} to v{req.version} (now v{new_version}) with AST safety check."
        },
    )

    return {
        "status": "ROLLED_BACK",
        "artifact_id": found_art.id,
        "name": found_art.name,
        "version": new_version,
        "rolled_back_to": req.version,
        "content": target_content,
    }


@app.post("/api/v1/missions/{mission_id}/pr")
async def generate_mission_pr(mission_id: str, req: PullRequestAPIRequest):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    from mas.core.state import SubsystemClass, Task, TaskPriority

    task = Task(
        id=f"TASK-{mission_id.split('-')[-1]}",
        title=session.title,
        description=session.description,
        priority=TaskPriority.HIGH,
        assigned_pod=SubsystemClass.FULL_SYSTEM,
    )

    pr_gen = PullRequestGenerator(repo_path=".")
    pr = pr_gen.synthesize_pull_request(
        task=task,
        blackboard=session.blackboard,
        source_branch=f"feature/{session.mission_id.lower()}",
        target_branch="main",
    )

    sub_result = pr_gen.submit_pull_request(
        pr=pr,
        push_to_remote=req.push,
        create_github_pr=req.create_pr,
    )

    return {
        "pr_id": pr.pr_id,
        "title": pr.title,
        "markdown": pr.description_markdown,
        "modified_files": pr.modified_files,
        "status_message": sub_result.status_message,
        "github_pr_url": sub_result.github_pr_url,
    }


@app.post("/api/v1/missions/{mission_id}/commit")
async def commit_mission_artifacts(mission_id: str, req: CommitAPIRequest = CommitAPIRequest()):
    registry = get_mission_registry()
    session = registry.get_mission(mission_id)
    if not session:
        raise HTTPException(status_code=404, detail="Mission not found")

    from mas.core.vcs import create_local_git_snapshot

    commit_res = create_local_git_snapshot(
        repo_path=".",
        commit_message=req.message or f"feat({mission_id.lower()}): snapshot synthesized artifacts",
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

    return commit_res.model_dump()


# Static web UI serving
if WEB_DIR.is_dir():
    app.mount("/vendor", StaticFiles(directory=str(WEB_DIR / "vendor")), name="vendor")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(WEB_DIR / "index.html"), media_type="text/html")

    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(str(WEB_DIR / "styles.css"), media_type="text/css")

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(str(WEB_DIR / "app.js"), media_type="text/javascript")

    @app.get("/app.jsx")
    async def serve_jsx():
        return FileResponse(str(WEB_DIR / "app.jsx"), media_type="text/javascript")
