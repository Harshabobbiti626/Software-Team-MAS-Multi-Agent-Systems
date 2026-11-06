"""
Isolated Process & Container Sandbox Execution Engine for MAS.
Supports ephemeral Docker container sandboxes with graceful fallback to host SubprocessSandbox.
Enforces timeout ceilings, memory bounds, and environment scrubbing.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

DANGEROUS_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-[rf]{1,2}\b\s+([/\\]|\*|[a-zA-Z]:[/\\])", re.IGNORECASE),
    re.compile(r"\brmdir\s+.*[/\\][sS]\b", re.IGNORECASE),
    re.compile(r"\bdel\s+.*[/\\][fFsS]\b\s+([/\\]|[a-zA-Z]:[/\\])", re.IGNORECASE),
    re.compile(r"\b(format|diskpart|mkfs|dd\s+if=)\b", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot|init\s+0|halt)\b", re.IGNORECASE),
    re.compile(r"\|\s*(sh|bash|powershell|cmd\.exe)\b", re.IGNORECASE),
    re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|powershell)", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),  # Fork bomb
]


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

    def _verify_security_guardrails(self, command_args: List[str], cwd: Optional[str]) -> Path:
        """Enforces path containment, binary whitelisting, and anti-destructive filtering."""
        if not command_args:
            raise ValueError("No command arguments provided.")

        raw_binary = Path(command_args[0]).name.lower().replace(".exe", "")
        if raw_binary not in self.allowed_binaries:
            raise PermissionError(
                f"Security Sandbox Violation: Binary '{command_args[0]}' (resolved as '{raw_binary}') is not permitted. "
                f"Allowed binaries: {self.allowed_binaries}"
            )

        cmd_string = " ".join(command_args)
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if pattern.search(cmd_string):
                raise PermissionError(
                    f"Security Sandbox Violation: Command '{cmd_string[:80]}' triggered destructive or unsafe execution pattern."
                )

        exec_cwd = (self.workspace_root / (cwd or "")).resolve()
        try:
            exec_cwd.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Security Sandbox Violation: Working directory '{exec_cwd}' escapes workspace jail '{self.workspace_root}'."
            )

        return exec_cwd

    def execute(
        self,
        command_args: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxResult:
        exec_cwd = self._verify_security_guardrails(command_args, cwd)
        exec_timeout = timeout or self.default_timeout

        # Scrub sensitive environment variables
        safe_env = os.environ.copy()
        for sensitive_key in [
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN",
            "SECRET_KEY",
            "PRIVATE_KEY",
        ]:
            safe_env.pop(sensitive_key, None)

        if env_vars:
            safe_env.update(env_vars)

        # Resolve command if not found directly in PATH (e.g. pytest, ruff, mypy on Windows)
        resolved_args = list(command_args)
        if resolved_args and shutil.which(resolved_args[0]) is None:
            if resolved_args[0] in ("pytest", "ruff", "mypy"):
                resolved_args = [sys.executable, "-m", resolved_args[0], *resolved_args[1:]]
            elif resolved_args[0] in ("python", "py"):
                resolved_args = [sys.executable, *resolved_args[1:]]

        import time

        start_time = time.time()
        try:
            process = subprocess.run(
                resolved_args,
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
                stdout=te.stdout
                if isinstance(te.stdout, str)
                else (te.stdout.decode("utf-8", errors="replace") if te.stdout else ""),
                stderr=te.stderr
                if isinstance(te.stderr, str)
                else (
                    te.stderr.decode("utf-8", errors="replace")
                    if te.stderr
                    else "Execution timed out."
                ),
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
    Executes commands inside ephemeral Docker containers with optional network isolation and resource ceilings.
    """

    def __init__(
        self,
        workspace_root: str = ".",
        image: str = "python:3.13-slim",
        default_timeout: int = 60,
        isolate_network: bool = False,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.image = image
        self.default_timeout = default_timeout
        self.isolate_network = isolate_network

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
            "1.5g",
            "--cpus",
            "2",
            "--pids-limit",
            "120",
        ]

        if self.isolate_network:
            docker_cmd.extend(["--network", "none"])

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


def get_sandbox_runner(
    workspace_root: str = ".", prefer_docker: bool = False, isolate_network: bool = False
):
    """Factory selecting DockerSandbox if available/requested, else SubprocessSandbox."""
    if prefer_docker:
        docker_runner = DockerSandbox(
            workspace_root=workspace_root, isolate_network=isolate_network
        )
        if docker_runner.is_available():
            return docker_runner
    return SubprocessSandbox(workspace_root=workspace_root)
