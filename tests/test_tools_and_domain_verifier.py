from pathlib import Path

import pytest

from mas.tools.domain_verifier import DomainVerifier
from mas.tools.file_ops import SafeFileOps
from mas.tools.linter import DeterministicLinter


def test_safe_file_ops(tmp_path):
    ops = SafeFileOps(workspace_root=str(tmp_path))
    written_path = ops.write_file("sub/test.txt", "hello world")
    assert Path(written_path).exists()
    assert ops.read_file("sub/test.txt") == "hello world"

    # Traversal attack protection
    with pytest.raises(PermissionError):
        ops.read_file("../../outside.txt")


def test_domain_verifier_secrets():
    verifier = DomainVerifier()
    dirty_content = "password = 'super_secret_value'"
    res = verifier.verify_content(dirty_content)
    assert not res.is_valid
    assert len(res.violations) > 0


def test_linter_ast():
    linter = DeterministicLinter()
    clean_code = "def valid():\n    return 42\n"
    res1 = linter.check_python_syntax_ast("clean.py", clean_code)
    assert res1.passed is True

    bad_code = "def broken(:\n    pass\n"
    res2 = linter.check_python_syntax_ast("broken.py", bad_code)
    assert res2.passed is False
    assert res2.error_count == 1


def test_polyglot_syntax_verification():
    linter = DeterministicLinter()

    # JSON Check
    json_good = '{"name": "MAS", "version": 2}'
    json_bad = '{"name": "MAS", "version": '
    assert linter.check_json_syntax("test.json", json_good).passed is True
    assert linter.check_json_syntax("test.json", json_bad).passed is False

    # YAML Check
    yaml_good = "service:\n  name: billing\n  port: 8080"
    yaml_bad = "service:\n  name: [unclosed list"
    assert linter.check_yaml_syntax("test.yaml", yaml_good).passed is True
    assert linter.check_yaml_syntax("test.yaml", yaml_bad).passed is False

    # TypeScript Check
    ts_good = "export const greet = (name: string): string => { return `Hello ${name}`; };"
    ts_bad_delimiter = "export const greet = (name: string): string => { return `Hello`; ;"  # missing closing brace
    ts_bad_quote = "const str = 'unclosed string;\nconst x = 1;"
    assert linter.check_typescript_syntax("App.tsx", ts_good).passed is True
    assert linter.check_typescript_syntax("App.tsx", ts_bad_delimiter).passed is False
    assert linter.check_typescript_syntax("App.tsx", ts_bad_quote).passed is False

    # SQL Check
    sql_good = "CREATE TABLE users (id UUID PRIMARY KEY, name VARCHAR(255) NOT NULL);"
    sql_bad = "CREATE TABLE users (id UUID PRIMARY KEY, name VARCHAR(255) NOT NULL;"  # missing closing paren
    sql_invalid_start = "NOT_A_KEYWORD table users;"
    assert linter.check_sql_syntax("schema.sql", sql_good).passed is True
    assert linter.check_sql_syntax("schema.sql", sql_bad).passed is False
    assert linter.check_sql_syntax("schema.sql", sql_invalid_start).passed is False

    # Dockerfile Check
    docker_good = 'FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nCMD ["python", "main.py"]\n'
    docker_bad_instruction = "INVALID_CMD python:3.11\nWORKDIR /app\n"
    docker_no_from = "WORKDIR /app\nCOPY . .\n"
    assert linter.check_dockerfile_syntax("Dockerfile", docker_good).passed is True
    assert linter.check_dockerfile_syntax("Dockerfile", docker_bad_instruction).passed is False
    assert linter.check_dockerfile_syntax("Dockerfile", docker_no_from).passed is False

    # Auto Dispatcher
    assert linter.check_syntax_auto("main.py", "x = 10\n").passed is True
    assert linter.check_syntax_auto("Component.tsx", ts_good).passed is True
    assert linter.check_syntax_auto("migration.sql", sql_good).passed is True
    assert linter.check_syntax_auto("config.yaml", yaml_good).passed is True
    assert linter.check_syntax_auto("package.json", json_good).passed is True
    assert linter.check_syntax_auto("Dockerfile", docker_good).passed is True


def test_dependency_reconciler_python_and_node(tmp_path):
    from mas.tools.dependency_reconciler import DependencyReconciler

    reconciler = DependencyReconciler(workspace_root=str(tmp_path))

    # 1. Test Python import extraction and reconciliation
    python_code = """
import os
import sys
import stripe
import redis
from pydantic import BaseModel
"""
    # Create an initial requirements.txt that already has pydantic
    (tmp_path / "requirements.txt").write_text("pydantic>=2.0.0\n", encoding="utf-8")

    report = reconciler.reconcile_file(
        "service.py", code_content=python_code, project_root=tmp_path
    )
    assert report.success is True
    assert "stripe" in report.detected_imports
    assert "redis" in report.detected_imports
    assert "os" in report.detected_imports
    # 'pydantic' was already present, so missing should be stripe and redis
    assert "redis" in report.missing_dependencies
    assert "stripe" in report.missing_dependencies
    assert "pydantic" not in report.missing_dependencies

    # Check that requirements.txt was updated with missing dependencies
    req_content = (tmp_path / "requirements.txt").read_text(encoding="utf-8")
    assert "redis>=1.0.0" in req_content
    assert "stripe>=1.0.0" in req_content

    # 2. Test Node/TypeScript import extraction and reconciliation
    ts_code = """
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
"""
    package_json = tmp_path / "package.json"
    package_json.write_text('{"dependencies": {"react": "^18.0.0"}}', encoding="utf-8")

    ts_report = reconciler.reconcile_file("App.tsx", code_content=ts_code, project_root=tmp_path)
    assert ts_report.success is True
    assert "@tanstack/react-query" in ts_report.missing_dependencies
    assert "axios" in ts_report.missing_dependencies

    pkg_data = (tmp_path / "package.json").read_text(encoding="utf-8")
    assert "@tanstack/react-query" in pkg_data
    assert "axios" in pkg_data
