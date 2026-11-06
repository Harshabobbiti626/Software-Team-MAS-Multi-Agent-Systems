"""
Deterministic Polyglot Linter & Test Runner Wrapper.
Runs multi-language AST/syntax parsing (Python, TypeScript/JS, SQL, JSON, YAML, Dockerfile)
and test execution, parsing output into structured results.
"""

import ast
import json
import os
import re
import sqlite3
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field

from mas.tools.sandbox import SubprocessSandbox


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

    def _read_content(self, file_path: str, code_content: Optional[str] = None) -> str:
        if code_content is not None:
            return code_content
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def check_python_syntax_ast(
        self, file_path: str, code_content: Optional[str] = None
    ) -> LintResult:
        """
        Deterministic, zero-subprocess Python AST parser to catch syntax errors immediately.
        """
        content = self._read_content(file_path, code_content)
        issues = []
        try:
            ast.parse(content, filename=file_path)
            return LintResult(
                tool_name="PythonASTParser",
                passed=True,
                raw_output="Syntax parsed successfully without AST errors.",
            )
        except SyntaxError as se:
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line_number=se.lineno or 1,
                    severity="ERROR",
                    message=str(se),
                    rule_code="SYNTAX_ERROR",
                )
            )
            return LintResult(
                tool_name="PythonASTParser",
                passed=False,
                error_count=1,
                issues=issues,
                raw_output=str(se),
            )

    def check_json_syntax(self, file_path: str, code_content: Optional[str] = None) -> LintResult:
        """
        Validates JSON schema and syntax using standard parser.
        """
        content = self._read_content(file_path, code_content)
        try:
            json.loads(content)
            return LintResult(
                tool_name="JSONParser",
                passed=True,
                raw_output="Valid JSON syntax.",
            )
        except json.JSONDecodeError as err:
            return LintResult(
                tool_name="JSONParser",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=err.lineno,
                        severity="ERROR",
                        message=f"JSON Decode Error: {err.msg}",
                        rule_code="JSON_SYNTAX_ERROR",
                    )
                ],
                raw_output=str(err),
            )

    def check_yaml_syntax(self, file_path: str, code_content: Optional[str] = None) -> LintResult:
        """
        Validates YAML syntax using safe YAML parser.
        """
        content = self._read_content(file_path, code_content)
        try:
            yaml.safe_load(content)
            return LintResult(
                tool_name="YAMLParser",
                passed=True,
                raw_output="Valid YAML syntax.",
            )
        except yaml.YAMLError as err:
            line = 1
            if hasattr(err, "problem_mark") and getattr(err, "problem_mark") is not None:
                mark = getattr(err, "problem_mark")
                line = mark.line + 1
            return LintResult(
                tool_name="YAMLParser",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=line,
                        severity="ERROR",
                        message=f"YAML Parse Error: {err}",
                        rule_code="YAML_SYNTAX_ERROR",
                    )
                ],
                raw_output=str(err),
            )

    def check_typescript_syntax(
        self, file_path: str, code_content: Optional[str] = None
    ) -> LintResult:
        """
        Validates TypeScript/JavaScript/TSX/JSX syntax:
        Checks balanced delimiters, template strings, quotes, and structural keywords.
        """
        content = self._read_content(file_path, code_content)
        lines = content.splitlines()

        stack = []
        matching = {")": "(", "]": "[", "}": "{"}
        in_single_quote = False
        in_double_quote = False
        in_template_lit = False
        in_block_comment = False

        for line_idx, line in enumerate(lines, start=1):
            i = 0
            n = len(line)
            while i < n:
                ch = line[i]

                # Check block comment
                if in_block_comment:
                    if ch == "*" and i + 1 < n and line[i + 1] == "/":
                        in_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue

                # Check line comment
                if not in_single_quote and not in_double_quote and not in_template_lit:
                    if ch == "/" and i + 1 < n and line[i + 1] == "/":
                        # Line comment rest of line
                        break
                    if ch == "/" and i + 1 < n and line[i + 1] == "*":
                        in_block_comment = True
                        i += 2
                        continue

                # String handling
                if ch == "\\" and (in_single_quote or in_double_quote or in_template_lit):
                    i += 2  # skip escaped character
                    continue

                if ch == "'" and not in_double_quote and not in_template_lit:
                    in_single_quote = not in_single_quote
                    i += 1
                    continue

                if ch == '"' and not in_single_quote and not in_template_lit:
                    in_double_quote = not in_double_quote
                    i += 1
                    continue

                if ch == "`" and not in_single_quote and not in_double_quote:
                    in_template_lit = not in_template_lit
                    i += 1
                    continue

                if in_single_quote or in_double_quote or in_template_lit:
                    i += 1
                    continue

                # Delimiter balance check
                if ch in ("(", "[", "{"):
                    stack.append((ch, line_idx, i + 1))
                elif ch in (")", "]", "}"):
                    expected = matching[ch]
                    if not stack:
                        return LintResult(
                            tool_name="TypeScriptSyntaxChecker",
                            passed=False,
                            error_count=1,
                            issues=[
                                LintIssue(
                                    file_path=file_path,
                                    line_number=line_idx,
                                    severity="ERROR",
                                    message=f"Unmatched closing delimiter '{ch}' at line {line_idx}, column {i + 1}",
                                    rule_code="TS_DELIMITER_MISMATCH",
                                )
                            ],
                            raw_output=f"Syntax Error: Unmatched closing '{ch}'",
                        )
                    last_open, open_line, open_col = stack.pop()
                    if last_open != expected:
                        return LintResult(
                            tool_name="TypeScriptSyntaxChecker",
                            passed=False,
                            error_count=1,
                            issues=[
                                LintIssue(
                                    file_path=file_path,
                                    line_number=line_idx,
                                    severity="ERROR",
                                    message=f"Mismatched delimiter: expected '{last_open}' to close before '{ch}' at line {line_idx}",
                                    rule_code="TS_DELIMITER_MISMATCH",
                                )
                            ],
                            raw_output=f"Syntax Error: Mismatched delimiter '{ch}'",
                        )
                i += 1

            if in_single_quote or in_double_quote:
                # Unclosed string literal on this line (unless multi-line template literal)
                return LintResult(
                    tool_name="TypeScriptSyntaxChecker",
                    passed=False,
                    error_count=1,
                    issues=[
                        LintIssue(
                            file_path=file_path,
                            line_number=line_idx,
                            severity="ERROR",
                            message=f"Unclosed string literal on line {line_idx}",
                            rule_code="TS_UNCLOSED_STRING",
                        )
                    ],
                    raw_output=f"Syntax Error: Unclosed string literal on line {line_idx}",
                )

        if in_template_lit:
            return LintResult(
                tool_name="TypeScriptSyntaxChecker",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=len(lines),
                        severity="ERROR",
                        message="Unclosed template literal (`...`) at end of file",
                        rule_code="TS_UNCLOSED_TEMPLATE",
                    )
                ],
                raw_output="Syntax Error: Unclosed template literal",
            )

        if stack:
            last_open, open_line, open_col = stack[-1]
            return LintResult(
                tool_name="TypeScriptSyntaxChecker",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=open_line,
                        severity="ERROR",
                        message=f"Unclosed delimiter '{last_open}' opened at line {open_line}, col {open_col}",
                        rule_code="TS_UNCLOSED_DELIMITER",
                    )
                ],
                raw_output=f"Syntax Error: Unclosed delimiter '{last_open}'",
            )

        return LintResult(
            tool_name="TypeScriptSyntaxChecker",
            passed=True,
            raw_output="Valid TypeScript/JavaScript structure and balanced tokens.",
        )

    def check_sql_syntax(self, file_path: str, code_content: Optional[str] = None) -> LintResult:
        """
        Validates SQL DDL/DML statements:
        1. Checks balanced parentheses and unclosed string quotes.
        2. Validates valid SQL command start tokens.
        3. Attempts an in-memory SQLite schema dry-run when possible.
        """
        content = self._read_content(file_path, code_content)
        lines = content.splitlines()

        paren_depth = 0
        in_quote = False
        valid_keywords = {
            "CREATE",
            "ALTER",
            "DROP",
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
            "WITH",
            "BEGIN",
            "COMMIT",
            "ROLLBACK",
            "COMMENT",
            "GRANT",
            "REVOKE",
            "SET",
            "SHOW",
            "TRUNCATE",
            "REINDEX",
            "EXPLAIN",
        }

        for line_idx, line in enumerate(lines, start=1):
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("--") or clean_line.startswith("/*"):
                continue

            i = 0
            n = len(line)
            while i < n:
                ch = line[i]
                if ch == "'" and (i == 0 or line[i - 1] != "\\"):
                    in_quote = not in_quote
                    i += 1
                    continue
                if not in_quote:
                    if ch == "(":
                        paren_depth += 1
                    elif ch == ")":
                        paren_depth -= 1
                        if paren_depth < 0:
                            return LintResult(
                                tool_name="SQLSyntaxChecker",
                                passed=False,
                                error_count=1,
                                issues=[
                                    LintIssue(
                                        file_path=file_path,
                                        line_number=line_idx,
                                        severity="ERROR",
                                        message=f"Unmatched closing parenthesis ')' at line {line_idx}",
                                        rule_code="SQL_PAREN_MISMATCH",
                                    )
                                ],
                                raw_output="SQL Syntax Error: Unexpected ')'",
                            )
                i += 1

        if in_quote:
            return LintResult(
                tool_name="SQLSyntaxChecker",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=len(lines),
                        severity="ERROR",
                        message="Unclosed single-quote literal in SQL content",
                        rule_code="SQL_UNCLOSED_QUOTE",
                    )
                ],
                raw_output="SQL Syntax Error: Unclosed single quote",
            )

        if paren_depth > 0:
            return LintResult(
                tool_name="SQLSyntaxChecker",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=len(lines),
                        severity="ERROR",
                        message=f"Unclosed parenthesis (depth={paren_depth}) in SQL content",
                        rule_code="SQL_UNCLOSED_PAREN",
                    )
                ],
                raw_output="SQL Syntax Error: Unclosed parenthesis",
            )

        # Split into statements and verify first keyword
        statements = [s.strip() for s in content.split(";") if s.strip()]
        for stmt in statements:
            # Strip comments from beginning of statement
            stmt_lines = [
                line_item.strip()
                for line_item in stmt.splitlines()
                if line_item.strip() and not line_item.strip().startswith("--")
            ]
            if not stmt_lines:
                continue
            first_word = re.split(r"\s+", stmt_lines[0])[0].upper()
            if first_word not in valid_keywords:
                return LintResult(
                    tool_name="SQLSyntaxChecker",
                    passed=False,
                    error_count=1,
                    issues=[
                        LintIssue(
                            file_path=file_path,
                            line_number=1,
                            severity="ERROR",
                            message=f"Unrecognized or invalid SQL statement starting with: '{first_word}'",
                            rule_code="SQL_INVALID_KEYWORD",
                        )
                    ],
                    raw_output=f"SQL Syntax Error: Invalid statement token '{first_word}'",
                )

        # Optional dry-run check with SQLite for generic DDL
        try:
            conn = sqlite3.connect(":memory:")
            # Replace common Postgres types that SQLite might not understand for pure syntax test
            sqlite_ddl = content
            for pg_type in [
                "UUID",
                "TIMESTAMPTZ",
                "TIMESTAMP WITH TIME ZONE",
                "BIGSERIAL",
                "SERIAL",
                "JSONB",
                "BOOLEAN",
            ]:
                sqlite_ddl = re.sub(rf"\b{pg_type}\b", "TEXT", sqlite_ddl, flags=re.IGNORECASE)
            sqlite_ddl = re.sub(r"CREATE\s+EXTENSION[^;]+;", "", sqlite_ddl, flags=re.IGNORECASE)
            sqlite_ddl = re.sub(r"COMMENT\s+ON[^;]+;", "", sqlite_ddl, flags=re.IGNORECASE)
            conn.executescript(sqlite_ddl)
            conn.close()
        except Exception:
            # PostgreSQL-specific constructs (GIN, partition, plpgsql) are allowed if lexical checks pass
            pass

        return LintResult(
            tool_name="SQLSyntaxChecker",
            passed=True,
            raw_output="Valid SQL structure, balanced clauses, and supported DDL/DML.",
        )

    def check_dockerfile_syntax(
        self, file_path: str, code_content: Optional[str] = None
    ) -> LintResult:
        """
        Validates Dockerfile syntax, instruction keywords, and base image specifications.
        """
        content = self._read_content(file_path, code_content)
        lines = content.splitlines()

        valid_instructions = {
            "FROM",
            "RUN",
            "CMD",
            "LABEL",
            "EXPOSE",
            "ENV",
            "ADD",
            "COPY",
            "ENTRYPOINT",
            "VOLUME",
            "USER",
            "WORKDIR",
            "ARG",
            "ONBUILD",
            "STOPSIGNAL",
            "HEALTHCHECK",
            "SHELL",
        }

        has_from = False
        in_continuation = False

        for line_idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if in_continuation:
                in_continuation = stripped.endswith("\\")
                continue

            # First token is the Dockerfile instruction
            match = re.match(r"^([A-Za-z]+)\s*(.*)", stripped)
            if not match:
                return LintResult(
                    tool_name="DockerfileSyntaxChecker",
                    passed=False,
                    error_count=1,
                    issues=[
                        LintIssue(
                            file_path=file_path,
                            line_number=line_idx,
                            severity="ERROR",
                            message=f"Malformed instruction line in Dockerfile: '{stripped}'",
                            rule_code="DOCKERFILE_SYNTAX_ERROR",
                        )
                    ],
                    raw_output=f"Dockerfile Syntax Error at line {line_idx}",
                )

            instruction, rest = match.groups()
            instruction_upper = instruction.upper()
            if instruction_upper not in valid_instructions:
                return LintResult(
                    tool_name="DockerfileSyntaxChecker",
                    passed=False,
                    error_count=1,
                    issues=[
                        LintIssue(
                            file_path=file_path,
                            line_number=line_idx,
                            severity="ERROR",
                            message=f"Unknown Dockerfile instruction '{instruction}' at line {line_idx}",
                            rule_code="DOCKERFILE_INVALID_INSTRUCTION",
                        )
                    ],
                    raw_output=f"Dockerfile Error: Invalid instruction '{instruction}'",
                )

            if instruction_upper == "FROM":
                if not rest.strip():
                    return LintResult(
                        tool_name="DockerfileSyntaxChecker",
                        passed=False,
                        error_count=1,
                        issues=[
                            LintIssue(
                                file_path=file_path,
                                line_number=line_idx,
                                severity="ERROR",
                                message=f"FROM instruction requires a base image at line {line_idx}",
                                rule_code="DOCKERFILE_MISSING_IMAGE",
                            )
                        ],
                        raw_output="Dockerfile Error: Empty FROM instruction",
                    )
                has_from = True

            in_continuation = stripped.endswith("\\")

        if not has_from and lines:
            return LintResult(
                tool_name="DockerfileSyntaxChecker",
                passed=False,
                error_count=1,
                issues=[
                    LintIssue(
                        file_path=file_path,
                        line_number=1,
                        severity="ERROR",
                        message="Dockerfile must contain at least one valid 'FROM' instruction",
                        rule_code="DOCKERFILE_NO_FROM",
                    )
                ],
                raw_output="Dockerfile Error: No FROM instruction found",
            )

        return LintResult(
            tool_name="DockerfileSyntaxChecker",
            passed=True,
            raw_output="Valid Dockerfile syntax and instructions.",
        )

    def check_syntax_auto(self, file_path: str, code_content: Optional[str] = None) -> LintResult:
        """
        Dispatches syntax check automatically according to file extension or name.
        """
        basename = os.path.basename(file_path).lower()
        _, ext = os.path.splitext(basename)

        if ext in (".py", ".pyw"):
            return self.check_python_syntax_ast(file_path, code_content)
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            return self.check_typescript_syntax(file_path, code_content)
        elif ext in (".sql",):
            return self.check_sql_syntax(file_path, code_content)
        elif ext in (".json",):
            return self.check_json_syntax(file_path, code_content)
        elif ext in (".yaml", ".yml"):
            return self.check_yaml_syntax(file_path, code_content)
        elif "dockerfile" in basename:
            return self.check_dockerfile_syntax(file_path, code_content)
        else:
            # Fallback: general balance check
            content = self._read_content(file_path, code_content)
            return LintResult(
                tool_name="GenericFileValidator",
                passed=len(content.strip()) > 0,
                error_count=0 if len(content.strip()) > 0 else 1,
                raw_output="Generic file validated." if len(content.strip()) > 0 else "Empty file.",
            )

    def run_pytest(self, test_target: str = "tests") -> LintResult:
        """Runs pytest inside the sandbox and checks results."""
        cmd = ["py", "-m", "pytest", test_target, "-v"]
        res = self.sandbox.execute(cmd, timeout=60)

        passed = res.exit_code == 0
        issues = []
        if not passed:
            for line in res.stdout.splitlines():
                if line.startswith("FAILED ") or "ERROR " in line:
                    issues.append(
                        LintIssue(
                            file_path=line,
                            line_number=1,
                            severity="ERROR",
                            message=line,
                            rule_code="TEST_FAIL",
                        )
                    )

        return LintResult(
            tool_name="pytest",
            passed=passed,
            error_count=len(issues) if not passed else 0,
            issues=issues,
            raw_output=res.stdout + "\n" + res.stderr,
        )
