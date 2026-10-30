"""
Isolated Process & Container Sandbox Execution Engine for MAS.
Supports ephemeral Docker container sandboxes with graceful fallback to host SubprocessSandbox.
Enforces timeout ceilings, memory bounds, and environment scrubbing.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel


class SandboxResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    runtime_environment: str = "host_subprocess"  # "docker" vs "host_subprocess"


class SubprocessSandbox:
    def __init__(
        self,
        workspace_root: str = ".",
        default_timeout: int = 45,
        allowed_binaries: Optional[List[str]] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout = default_timeout
        self.allowed_binaries = allowed_binaries or [
            "python",
            "py",
            "pytest",
            "git",
            "ruff",
            "mypy",
            "node",
            "npm",
        ]

    def execute(
        self,
        command_args: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        if not command_args:
            raise ValueError("No command arguments provided")

        binary = command_args[0].lower().replace(".exe", "")
        # Whitelist check
        if binary not in self.allowed_binaries and not any(
            binary.endswith(b) for b in self.allowed_binaries
        ):
            raise PermissionError(
                f"Binary '{command_args[0]}' is not in the allowed sandbox binaries list."
            )

        exec_cwd = (self.workspace_root / (cwd or "")).resolve()
        exec_timeout = timeout or self.default_timeout

        # Scrub sensitive environment variables
        safe_env = os.environ.copy()
        for sensitive_key in [
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
        ]:
            safe_env.pop(sensitive_key, None)

        if env_vars:
            safe_env.update(env_vars)

        import time

        start_time = time.time()
        try:
            process = subprocess.run(
                command_args,
                cwd=str(exec_cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=exec_timeout,
                env=safe_env,
            )
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                duration_seconds=duration,
                timed_out=False,
                runtime_environment="host_subprocess",
            )
        except subprocess.TimeoutExpired as te:
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=-1,
                stdout=te.stdout.decode("utf-8", errors="replace") if te.stdout else "",
                stderr=te.stderr.decode("utf-8", errors="replace")
                if te.stderr
                else "Execution timed out.",
                duration_seconds=duration,
                timed_out=True,
                runtime_environment="host_subprocess",
            )
        except Exception as e:
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                duration_seconds=duration,
                timed_out=False,
                runtime_environment="host_subprocess",
            )


class DockerSandbox:
    """
    Executes commands inside ephemeral Docker containers for strong kernel-level isolation.
    """

    def __init__(
        self, workspace_root: str = ".", image: str = "python:3.13-slim", default_timeout: int = 60
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.image = image
        self.default_timeout = default_timeout

    def is_available(self) -> bool:
        """Verifies if docker CLI is available and docker daemon responds."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute(
        self,
        command_args: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        if not self.is_available():
            raise RuntimeError("Docker is not running or accessible on the host system.")

        import time

        start_time = time.time()
        exec_timeout = timeout or self.default_timeout
        container_workdir = "/workspace"

        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{str(self.workspace_root)}:{container_workdir}",
            "-w",
            container_workdir,
            "--memory",
            "2g",
            "--cpus",
            "2",
        ]

        if env_vars:
            for k, v in env_vars.items():
                docker_cmd.extend(["-e", f"{k}={v}"])

        docker_cmd.append(self.image)
        docker_cmd.extend(command_args)

        try:
            process = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=exec_timeout,
            )
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                duration_seconds=duration,
                timed_out=False,
                runtime_environment="docker",
            )
        except subprocess.TimeoutExpired as te:
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=-1,
                stdout=(
                    te.stdout.decode("utf-8", errors="replace")
                    if isinstance(te.stdout, bytes)
                    else (te.stdout or "")
                ),
                stderr=(
                    te.stderr.decode("utf-8", errors="replace")
                    if isinstance(te.stderr, bytes)
                    else (te.stderr or "Container execution timed out.")
                ),
                duration_seconds=duration,
                timed_out=True,
                runtime_environment="docker",
            )
        except Exception as e:
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=-1,
                stdout="",
                stderr=f"Docker container error: {str(e)}",
                duration_seconds=duration,
                timed_out=False,
                runtime_environment="docker",
            )


def get_sandbox_runner(workspace_root: str = ".", prefer_docker: bool = False):
    """Factory selecting DockerSandbox if available/requested, else SubprocessSandbox."""
    if prefer_docker:
        docker_runner = DockerSandbox(workspace_root=workspace_root)
        if docker_runner.is_available():
            return docker_runner
    return SubprocessSandbox(workspace_root=workspace_root)
