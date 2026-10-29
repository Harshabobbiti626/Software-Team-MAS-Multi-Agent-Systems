import pytest
from pathlib import Path
from mas.tools.file_ops import SafeFileOps
from mas.tools.domain_verifier import DomainVerifier
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
