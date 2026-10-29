"""
Deterministic Linter & Test Runner Wrapper.
Runs pytest, ruff, mypy, and Python AST sanity checks, parsing output into structured results.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from mas.tools.sandbox import SubprocessSandbox, SandboxResult


class LintIssue(BaseModel):
    file_path: str
    line_number: int = 1
    severity: str = "ERROR"
    message: str
    rule_code: Optional[str] = None


class LintResult(BaseModel):
    tool_name: str
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    issues: List[LintIssue] = Field(default_factory=list)
    raw_output: str = ""


class DeterministicLinter:
    def __init__(self, sandbox: Optional[SubprocessSandbox] = None):
        self.sandbox = sandbox or SubprocessSandbox()

    def check_python_syntax_ast(self, file_path: str, code_content: Optional[str] = None) -> LintResult:
        """
        Deterministic, zero-subprocess Python AST parser to catch syntax errors immediately.
        """
        issues = []
        try:
            if code_content is None:
                with open(file_path, "r", encoding="utf-8") as f:
                    code_content = f.read()
            ast.parse(code_content, filename=file_path)
            return LintResult(
                tool_name="PythonASTParser",
                passed=True,
                raw_output="Syntax parsed successfully without AST errors."
            )
        except SyntaxError as se:
            issues.append(LintIssue(
                file_path=file_path,
                line_number=se.lineno or 1,
                severity="ERROR",
                message=str(se),
                rule_code="SYNTAX_ERROR"
            ))
            return LintResult(
                tool_name="PythonASTParser",
                passed=False,
                error_count=1,
                issues=issues,
                raw_output=str(se)
            )

    def run_pytest(self, test_target: str = "tests") -> LintResult:
        """Runs pytest inside the sandbox and checks results."""
        cmd = ["py", "-m", "pytest", test_target, "-v"]
        res = self.sandbox.execute(cmd, timeout=60)

        passed = (res.exit_code == 0)
        issues = []
        if not passed:
            for line in res.stdout.splitlines():
                if line.startswith("FAILED ") or "ERROR " in line:
                    issues.append(LintIssue(
                        file_path=line,
                        line_number=1,
                        severity="ERROR",
                        message=line,
                        rule_code="TEST_FAIL"
                    ))

        return LintResult(
            tool_name="pytest",
            passed=passed,
            error_count=len(issues) if not passed else 0,
            issues=issues,
            raw_output=res.stdout + "\n" + res.stderr
        )
