"""
Pytest configuration and global path resolution for MAS test suite.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root is always accessible in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def ensure_deterministic_test_env(monkeypatch):
    """Enforces deterministic offline mock LLM during automated test suite runs."""
    monkeypatch.setenv("MAS_LLM_PROVIDER", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
