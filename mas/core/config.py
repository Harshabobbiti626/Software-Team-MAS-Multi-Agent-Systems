"""
System Configuration Engine for MAS.
Loads settings from YAML files or environment variables with strict Pydantic validation.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class SystemSettings(BaseModel):
    environment: str = "development"
    log_level: str = "INFO"
    deterministic_mode: bool = True
    blackboard_repo_path: str = "."


class LimitSettings(BaseModel):
    max_turns_per_agent: int = 5
    max_total_turns_per_task: int = 30
    max_prompt_tokens: int = 128000
    max_candidate_tokens: int = 16384
    max_thinking_tokens: int = 65536
    max_consecutive_failures: int = 3
    circuit_breaker_enabled: bool = True
    task_timeout_seconds: int = 300


class CognitionSettings(BaseModel):
    enable_extended_thinking: bool = True
    enable_pre_mortem: bool = True
    enable_tradeoff_matrix: bool = True
    default_thinking_budget: int = 4096
    high_stakes_thinking_budget: int = 16384


class MemorySettings(BaseModel):
    working_memory_window: int = 10
    compaction_threshold_tokens: int = 8000
    sqlite_db_path: str = ".mas_episodic.db"
    enable_semantic_cache: bool = True


class ModelSettings(BaseModel):
    default_model: str = "gemini-2.5-pro"
    fast_model: str = "gemini-2.5-flash"
    reasoning_model: str = "gemini-3.0-thinking"
    roles: Dict[str, str] = Field(default_factory=dict)


class SandboxSettings(BaseModel):
    default_timeout_seconds: int = 45
    enforce_isolation: bool = False
    allowed_binaries: List[str] = Field(default_factory=lambda: ["git", "python", "py", "pytest"])


class MASConfiguration(BaseModel):
    system: SystemSettings = Field(default_factory=SystemSettings)
    limits: LimitSettings = Field(default_factory=LimitSettings)
    cognition: CognitionSettings = Field(default_factory=CognitionSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    models: ModelSettings = Field(default_factory=ModelSettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)

    @classmethod
    def load_from_yaml(cls, path: Optional[Path | str] = None) -> "MASConfiguration":
        if path is None:
            default_path = Path("config/system_settings.yaml")
            if default_path.exists():
                path = default_path

        if path and Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
                data = raw_data if isinstance(raw_data, dict) else {}
            return cls(**data)
        return cls()


# Global Singleton Configuration accessor
_config_instance: Optional[MASConfiguration] = None


def get_config(reload: bool = False, config_path: Optional[str] = None) -> MASConfiguration:
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = MASConfiguration.load_from_yaml(config_path)
    return _config_instance
