from pydantic import BaseModel

from mas.core.config import load_dotenv_if_present
from mas.core.llm import (
    AnthropicRESTProvider,
    DeterministicMockLLMProvider,
    GeminiRESTProvider,
    LLMGenerationConfig,
    OpenAICompatibleProvider,
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


def test_llm_provider_factory(monkeypatch):
    # 1. Fallback to mock provider in clean offline environment
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MAS_LLM_PROVIDER", raising=False)

    provider = get_llm_provider()
    assert isinstance(provider, DeterministicMockLLMProvider)

    # 2. OpenAI provider selection
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key")
    p_openai = get_llm_provider()
    assert isinstance(p_openai, OpenAICompatibleProvider)
    assert p_openai.api_key == "sk-test-mock-key"

    # 3. Anthropic provider selection
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    p_anthropic = get_llm_provider()
    assert isinstance(p_anthropic, AnthropicRESTProvider)
    assert p_anthropic.api_key == "sk-ant-test-key"

    # 4. Gemini provider selection
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSy-real-key")
    p_gemini = get_llm_provider()
    assert isinstance(p_gemini, GeminiRESTProvider)
    assert p_gemini.api_key == "AIzaSy-real-key"


def test_native_dotenv_loader(tmp_path, monkeypatch):
    test_env = tmp_path / ".env.test"
    test_env.write_text(
        'CUSTOM_TEST_VAR=mas_value_123\n# A comment\nANOTHER_KEY="quoted_value"\n', encoding="utf-8"
    )
    monkeypatch.delenv("CUSTOM_TEST_VAR", raising=False)
    monkeypatch.delenv("ANOTHER_KEY", raising=False)

    load_dotenv_if_present(test_env)

    import os

    assert os.environ.get("CUSTOM_TEST_VAR") == "mas_value_123"
    assert os.environ.get("ANOTHER_KEY") == "quoted_value"


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
