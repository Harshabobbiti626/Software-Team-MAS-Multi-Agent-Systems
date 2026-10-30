from pydantic import BaseModel

from mas.core.llm import (
    DeterministicMockLLMProvider,
    GeminiRESTProvider,
    LLMGenerationConfig,
    get_llm_provider,
)
from mas.tools.patcher import SurgicalPatcher
from mas.tools.sandbox import SubprocessSandbox, get_sandbox_runner


class SampleValidationModel(BaseModel):
    id: str
    decision: str
    status: str


def test_mock_llm_provider_generation():
    provider = DeterministicMockLLMProvider()
    resp = provider.generate(
        prompt="Analyze database schema lock risk",
        config=LLMGenerationConfig(thinking_budget=2000),
    )
    assert resp.finish_reason == "STOP"
    assert resp.prompt_tokens > 0
    assert resp.thinking_tokens == 2000
    assert resp.total_tokens > 0
    assert resp.thoughts is not None
    assert "pre-mortem" in resp.thoughts.lower()


def test_mock_llm_structured_output():
    provider = DeterministicMockLLMProvider()
    obj, resp = provider.generate_structured(
        prompt="Review pull request #42", schema=SampleValidationModel
    )
    assert isinstance(obj, SampleValidationModel)
    assert obj.id == "MOCK-001"
    assert obj.status == "SUCCESS"
    assert obj.decision == "APPROVED"
    assert resp.finish_reason == "STOP"
    assert resp.structured_data is not None


def test_llm_provider_factory():
    # Should fallback to mock provider cleanly in offline / test environment
    provider = get_llm_provider()
    assert isinstance(provider, (DeterministicMockLLMProvider, GeminiRESTProvider))


def test_surgical_patcher_success(tmp_path):
    patcher = SurgicalPatcher(workspace_root=str(tmp_path))
    test_file = tmp_path / "service.py"
    test_file.write_text(
        "def compute_total(a, b):\n    return a + b\n\ndef validate():\n    return True\n",
        encoding="utf-8",
    )

    search = "def compute_total(a, b):\n    return a + b"
    replace = "def compute_total(a, b):\n    # Enhanced with bounds check\n    if a < 0 or b < 0:\n        raise ValueError('Negative value')\n    return a + b"

    res = patcher.apply_search_replace_block("service.py", search, replace)
    assert res.success is True
    assert "raise ValueError" in test_file.read_text(encoding="utf-8")


def test_surgical_patcher_syntax_error_rollback(tmp_path):
    patcher = SurgicalPatcher(workspace_root=str(tmp_path))
    test_file = tmp_path / "broken.py"
    original_code = "def valid():\n    return 100\n"
    test_file.write_text(original_code, encoding="utf-8")

    search = "return 100"
    replace = "return (broken syntax without closing parenthesis"

    res = patcher.apply_search_replace_block("broken.py", search, replace, verify_ast=True)
    assert res.success is False
    assert res.error_message is not None
    assert "syntax error" in res.error_message.lower()
    # File content must remain unchanged (atomic rollback)
    assert test_file.read_text(encoding="utf-8") == original_code


def test_surgical_patcher_block_text(tmp_path):
    patcher = SurgicalPatcher(workspace_root=str(tmp_path))
    test_file = tmp_path / "module.py"
    test_file.write_text("x = 10\ny = 20\n", encoding="utf-8")

    block = """<<<<<<< SEARCH
x = 10
=======
x = 999
>>>>>>> REPLACE"""

    res = patcher.parse_and_apply_block_text("module.py", block)
    assert res.success is True
    assert "x = 999" in test_file.read_text(encoding="utf-8")


def test_sandbox_factory(tmp_path):
    runner = get_sandbox_runner(workspace_root=str(tmp_path), prefer_docker=False)
    assert isinstance(runner, SubprocessSandbox)
