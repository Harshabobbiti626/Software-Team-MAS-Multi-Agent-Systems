"""
Isolated Subprocess Sandbox Execution Engine.
Runs commands with timeouts, environment scrubbing, and binary whitelisting.
"""

import os
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


class SubprocessSandbox:
    def __init__(
        self,
        workspace_root: str = ".",
        default_timeout: int = 45,
        allowed_binaries: Optional[List[str]] = None
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout = default_timeout
        self.allowed_binaries = allowed_binaries or ["python", "py", "pytest", "git", "ruff", "mypy"]

    def execute(
        self,
        command_args: List[str],
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> SandboxResult:
        if not command_args:
            raise ValueError("No command arguments provided")

        binary = command_args[0].lower().replace(".exe", "")
        # Whitelist check
        if binary not in self.allowed_binaries and not any(binary.endswith(b) for b in self.allowed_binaries):
            raise PermissionError(f"Binary '{command_args[0]}' is not in the allowed sandbox binaries list.")

        exec_cwd = (self.workspace_root / (cwd or "")).resolve()
        exec_timeout = timeout or self.default_timeout

        # Scrub sensitive environment variables
        safe_env = os.environ.copy()
        for sensitive_key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN"]:
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
                env=safe_env
            )
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                duration_seconds=duration,
                timed_out=False
            )
        except subprocess.TimeoutExpired as te:
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=-1,
                stdout=te.stdout.decode("utf-8", errors="replace") if te.stdout else "",
                stderr=te.stderr.decode("utf-8", errors="replace") if te.stderr else "Execution timed out.",
                duration_seconds=duration,
                timed_out=True
            )
        except Exception as e:
            duration = time.time() - start_time
            return SandboxResult(
                command=" ".join(command_args),
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                duration_seconds=duration,
                timed_out=False
            )
