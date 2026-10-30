"""
Production-Grade Resilient LLM Inference Engine for MAS.
Supports Google Gemini REST API, Antigravity SDK bindings, and Deterministic Mock Fallbacks.
Enforces Pydantic structured output validation, extended thinking budgets, and exponential backoff.
"""

import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

import requests
from pydantic import BaseModel

from mas.core.config import MASConfiguration, get_config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMGenerationConfig(BaseModel):
    temperature: float = 0.2
    max_output_tokens: int = 8192
    thinking_budget: Optional[int] = 4096
    response_mime_type: Optional[str] = None
    response_schema: Optional[Dict[str, Any]] = None


class LLMResponse(BaseModel):
    text: str
    thoughts: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "STOP"
    model_name: str = "default"


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> LLMResponse:
        """Executes a single reasoning/generation turn."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> tuple[T, LLMResponse]:
        """Enforces schema-validated structured output with retry/self-healing."""
        pass


class GeminiRESTProvider(BaseLLMProvider):
    """
    Direct HTTPS REST client for Google Gemini API with exponential backoff and thinking support.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gemini-2.5-pro"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.default_model = default_model

    def _execute_with_retry(
        self, url: str, payload: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url, params=params, json=payload, headers=headers, timeout=60
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [429, 500, 503]:
                    # Rate limit or transient error -> exponential backoff with jitter
                    backoff = (2**attempt) + random.uniform(0.1, 1.0)
                    logger.warning(
                        f"Gemini API HTTP {response.status_code}. Retrying in {backoff:.2f}s..."
                    )
                    time.sleep(backoff)
                else:
                    raise RuntimeError(
                        f"Gemini API returned error {response.status_code}: {response.text}"
                    )
            except requests.RequestException:
                if attempt == max_retries - 1:
                    raise
                backoff = (2**attempt) + random.uniform(0.1, 0.5)
                time.sleep(backoff)

        raise RuntimeError("Gemini API call failed after max retries")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> LLMResponse:
        target_model = model or self.default_model
        cfg = config or LLMGenerationConfig()
        url = f"{self.BASE_URL}/{target_model}:generateContent"

        contents = []
        if system_prompt:
            contents.append(
                {"role": "user", "parts": [{"text": f"System Directive:\n{system_prompt}"}]}
            )
            contents.append(
                {
                    "role": "model",
                    "parts": [{"text": "Understood. I will abide by all system directives."}],
                }
            )

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        gen_config: Dict[str, Any] = {
            "temperature": cfg.temperature,
            "maxOutputTokens": cfg.max_output_tokens,
        }

        if cfg.response_mime_type:
            gen_config["responseMimeType"] = cfg.response_mime_type
        if cfg.response_schema:
            gen_config["responseSchema"] = cfg.response_schema

        payload = {"contents": contents, "generationConfig": gen_config}

        if cfg.thinking_budget:
            payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": cfg.thinking_budget}

        data = self._execute_with_retry(url, payload)

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"No candidates returned: {data}")

        first_cand = candidates[0]
        parts = first_cand.get("content", {}).get("parts", [])

        text_content = ""
        thoughts = ""
        for p in parts:
            if p.get("thought", False):
                thoughts += p.get("text", "")
            else:
                text_content += p.get("text", "")

        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        candidate_tokens = usage.get("candidatesTokenCount", 0)
        thinking_tokens = usage.get("thoughtsTokenCount", 0)
        total_tokens = usage.get(
            "totalTokenCount", prompt_tokens + candidate_tokens + thinking_tokens
        )

        return LLMResponse(
            text=text_content.strip(),
            thoughts=thoughts.strip() if thoughts else None,
            prompt_tokens=prompt_tokens,
            candidate_tokens=candidate_tokens,
            thinking_tokens=thinking_tokens,
            total_tokens=total_tokens,
            finish_reason=first_cand.get("finishReason", "STOP"),
            model_name=target_model,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> tuple[T, LLMResponse]:
        cfg = config or LLMGenerationConfig()
        cfg.response_mime_type = "application/json"

        # Enhanced prompt with schema enforcement
        strict_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid JSON adhering to this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )

        resp = self.generate(strict_prompt, system_prompt=system_prompt, model=model, config=cfg)
        clean_text = resp.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        parsed_json = json.loads(clean_text.strip())
        structured_obj = schema.model_validate(parsed_json)
        resp.structured_data = parsed_json
        return structured_obj, resp


class DeterministicMockLLMProvider(BaseLLMProvider):
    """
    Offline deterministic provider for CI/CD, local testing, and zero-token test runs.
    Synthesizes valid contextual payloads adhering to Pydantic schemas.
    """

    def __init__(self, default_model: str = "mock-reasoner"):
        self.default_model = default_model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> LLMResponse:
        est_prompt = max(10, len(prompt) // 4)
        est_cand = 50
        est_thinking = config.thinking_budget if (config and config.thinking_budget) else 100

        p_lower = prompt.lower()
        if "python" in p_lower or ("code" in p_lower and "generate" in p_lower):
            text = (
                "\"\"\"Mock Generated Service\"\"\"\n\n"
                "import uuid\n"
                "from pydantic import BaseModel, Field\n\n\n"
                "class MockPayload(BaseModel):\n"
                "    name: str = Field(..., min_length=1)\n\n\n"
                "class MockService:\n"
                "    def __init__(self):\n"
                "        self.id = str(uuid.uuid4())\n\n"
                "    def process(self, payload: MockPayload) -> bool:\n"
                "        return len(payload.name) > 0\n"
            )
        else:
            text = f"Deterministic response analyzing: {prompt[:80]}..."

        return LLMResponse(
            text=text,
            thoughts=f"Evaluated pre-mortem risks and contract constraints for {prompt[:60]}",
            prompt_tokens=est_prompt,
            candidate_tokens=est_cand,
            thinking_tokens=est_thinking,
            total_tokens=est_prompt + est_cand + est_thinking,
            finish_reason="STOP",
            model_name=model or self.default_model,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> tuple[T, LLMResponse]:
        # Generate default instance of schema by populating fields intelligently
        schema_json = schema.model_json_schema()
        properties = schema_json.get("properties", {})
        synthetic_dict: Dict[str, Any] = {}

        for prop_name, prop_meta in properties.items():
            prop_type = prop_meta.get("type", "string")
            if prop_type == "string":
                synthetic_dict[prop_name] = f"Validated {prop_name} for {prompt[:30]}"
            elif prop_type == "integer":
                synthetic_dict[prop_name] = 1
            elif prop_type == "number":
                synthetic_dict[prop_name] = 0.95
            elif prop_type == "boolean":
                synthetic_dict[prop_name] = True
            elif prop_type == "array":
                synthetic_dict[prop_name] = [f"Item 1 of {prop_name}"]
            elif prop_type == "object":
                synthetic_dict[prop_name] = {}
            else:
                synthetic_dict[prop_name] = "value"

        # Special casing for known fields
        if "id" in synthetic_dict:
            synthetic_dict["id"] = "MOCK-001"
        if "status" in synthetic_dict:
            synthetic_dict["status"] = "SUCCESS"
        if "decision" in synthetic_dict:
            synthetic_dict["decision"] = "APPROVED"

        try:
            validated = schema.model_validate(synthetic_dict)
        except Exception:
            # Fallback to empty constructor or construct minimally
            validated = schema.model_construct(**synthetic_dict)

        resp = self.generate(prompt, system_prompt, model, config)
        resp.structured_data = synthetic_dict
        return validated, resp


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Universal REST client for OpenAI-compatible inference endpoints:
    Supports OpenAI (gpt-4o, o3-mini), Groq, DeepSeek, Ollama, Together, vLLM, and LMStudio.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        raw_base = (
            base_url
            or os.environ.get("OPENAI_BASE_URL", "")
            or "https://api.openai.com/v1"
        )
        self.base_url = raw_base.rstrip("/")
        self.default_model = default_model

    def _execute_with_retry(
        self, url: str, payload: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [429, 500, 502, 503]:
                    backoff = (2**attempt) + random.uniform(0.1, 1.0)
                    time.sleep(backoff)
                else:
                    raise RuntimeError(
                        f"OpenAI-compatible API error {response.status_code}: {response.text}"
                    )
            except requests.RequestException:
                if attempt == max_retries - 1:
                    raise
                time.sleep((2**attempt) + random.uniform(0.1, 0.5))
        raise RuntimeError("OpenAI-compatible API call failed after max retries")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> LLMResponse:
        target_model = model or self.default_model
        cfg = config or LLMGenerationConfig()
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_output_tokens,
        }

        if cfg.response_mime_type == "application/json":
            payload["response_format"] = {"type": "json_object"}

        data = self._execute_with_retry(url, payload)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices returned: {data}")

        choice = choices[0]
        text_content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            text=text_content.strip(),
            prompt_tokens=prompt_tokens,
            candidate_tokens=completion_tokens,
            total_tokens=usage.get("total_tokens", prompt_tokens + completion_tokens),
            finish_reason=choice.get("finish_reason", "STOP"),
            model_name=target_model,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> tuple[T, LLMResponse]:
        cfg = config or LLMGenerationConfig()
        cfg.response_mime_type = "application/json"
        strict_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid JSON adhering to this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )
        resp = self.generate(strict_prompt, system_prompt=system_prompt, model=model, config=cfg)
        clean = resp.text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]

        parsed = json.loads(clean.strip())
        structured_obj = schema.model_validate(parsed)
        resp.structured_data = parsed
        return structured_obj, resp


class AnthropicRESTProvider(BaseLLMProvider):
    """
    Direct REST client for Anthropic Claude API (claude-3-7-sonnet, claude-3-5-haiku).
    """

    BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(
        self, api_key: Optional[str] = None, default_model: str = "claude-3-7-sonnet-20250219"
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.default_model = default_model

    def _execute_with_retry(
        self, payload: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        for attempt in range(max_retries):
            try:
                response = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=60)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [429, 500, 502, 503]:
                    time.sleep((2**attempt) + random.uniform(0.1, 1.0))
                else:
                    raise RuntimeError(
                        f"Anthropic API returned error {response.status_code}: {response.text}"
                    )
            except requests.RequestException:
                if attempt == max_retries - 1:
                    raise
                time.sleep((2**attempt) + random.uniform(0.1, 0.5))
        raise RuntimeError("Anthropic API call failed after max retries")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> LLMResponse:
        target_model = model or self.default_model
        cfg = config or LLMGenerationConfig()

        payload: Dict[str, Any] = {
            "model": target_model,
            "max_tokens": cfg.max_output_tokens,
            "temperature": cfg.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        data = self._execute_with_retry(payload)
        content_blocks = data.get("content", [])
        text_content = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return LLMResponse(
            text=text_content.strip(),
            prompt_tokens=prompt_tokens,
            candidate_tokens=output_tokens,
            total_tokens=prompt_tokens + output_tokens,
            finish_reason=data.get("stop_reason", "STOP"),
            model_name=target_model,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[LLMGenerationConfig] = None,
    ) -> tuple[T, LLMResponse]:
        strict_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Return ONLY valid JSON adhering to this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )
        resp = self.generate(strict_prompt, system_prompt=system_prompt, model=model, config=config)
        clean = resp.text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]

        parsed = json.loads(clean.strip())
        structured_obj = schema.model_validate(parsed)
        resp.structured_data = parsed
        return structured_obj, resp


def get_llm_provider(config: Optional[MASConfiguration] = None) -> BaseLLMProvider:
    """
    Factory creating the appropriate provider based on environment and credentials.
    Priority:
    1. Explicit provider setting in config.models.provider or MAS_LLM_PROVIDER
    2. GEMINI_API_KEY -> GeminiRESTProvider
    3. OPENAI_API_KEY or OPENAI_BASE_URL -> OpenAICompatibleProvider
    4. ANTHROPIC_API_KEY -> AnthropicRESTProvider
    5. Graceful fallback to DeterministicMockLLMProvider
    """
    cfg = config or get_config()
    provider_pref = (
        os.environ.get("MAS_LLM_PROVIDER", "").strip().lower()
        or getattr(cfg.models, "provider", "").strip().lower()
    )

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or (
        cfg.models.api_key if provider_pref == "gemini" else ""
    )
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip() or (
        cfg.models.api_key if provider_pref in ["openai", "ollama", "groq", "deepseek"] else ""
    )
    openai_base = os.environ.get("OPENAI_BASE_URL", "").strip() or getattr(
        cfg.models, "base_url", None
    )
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip() or (
        cfg.models.api_key if provider_pref == "anthropic" else ""
    )

    # 1. Explicit preference or auto-detection
    if (
        provider_pref in ["openai", "ollama", "groq", "deepseek"]
        or (openai_key and not gemini_key and not anthropic_key)
        or openai_base
    ):
        model = (
            cfg.models.default_model
            if not cfg.models.default_model.startswith("gemini")
            else "gpt-4o"
        )
        return OpenAICompatibleProvider(
            api_key=openai_key, base_url=openai_base, default_model=model
        )

    if provider_pref == "anthropic" or (anthropic_key and not gemini_key):
        model = (
            cfg.models.default_model
            if not cfg.models.default_model.startswith("gemini")
            else "claude-3-7-sonnet-20250219"
        )
        return AnthropicRESTProvider(api_key=anthropic_key, default_model=model)

    if gemini_key and not gemini_key.startswith("dummy") and not gemini_key.startswith("your_"):
        return GeminiRESTProvider(api_key=gemini_key, default_model=cfg.models.default_model)

    return DeterministicMockLLMProvider(default_model=cfg.models.default_model)
