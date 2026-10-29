"""
Base Agent Abstract Class for MAS.
Enforces schema-validated contracts, cognitive deliberation, multi-tier memory access,
live LLM inference, surgical code patching, and strict resource ceilings.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field

from mas.core.blackboard import ArtifactBlackboard
from mas.core.cognition import CognitiveEngine, PreMortemAnalysis
from mas.core.config import MASConfiguration, get_config
from mas.core.llm import BaseLLMProvider, LLMGenerationConfig, LLMResponse, get_llm_provider
from mas.core.state import Artifact, ArtifactType, SubsystemClass, Task, TokenUsageTracker
from mas.memory.episodic import EpisodicMemory
from mas.memory.procedural import ProceduralMemory
from mas.memory.semantic import SemanticMemory
from mas.memory.working import WorkingMemory
from mas.tools.patcher import PatchResult, SurgicalPatcher

T = TypeVar("T", bound=BaseModel)


class AgentResponse(BaseModel):
    agent_role: str
    status: str = "SUCCESS"  # "SUCCESS", "FAILED", "BLOCKED"
    summary: str
    artifacts_produced: List[str] = Field(default_factory=list)
    pre_mortem: Optional[PreMortemAnalysis] = None
    tokens_used: TokenUsageTracker = Field(default_factory=TokenUsageTracker)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    def __init__(
        self,
        role: str,
        pod: SubsystemClass,
        config: Optional[MASConfiguration] = None,
        blackboard: Optional[ArtifactBlackboard] = None,
        working_memory: Optional[WorkingMemory] = None,
        episodic_memory: Optional[EpisodicMemory] = None,
        semantic_memory: Optional[SemanticMemory] = None,
        procedural_memory: Optional[ProceduralMemory] = None,
        cognition: Optional[CognitiveEngine] = None,
        llm: Optional[BaseLLMProvider] = None,
        patcher: Optional[SurgicalPatcher] = None
    ):
        self.role = role
        self.pod = pod
        self.config = config or get_config()
        self.blackboard = blackboard or ArtifactBlackboard(repo_path=self.config.system.blackboard_repo_path)
        self.working_memory = working_memory or WorkingMemory(
            window_size=self.config.memory.working_memory_window,
            compaction_threshold=self.config.memory.compaction_threshold_tokens
        )
        self.episodic_memory = episodic_memory or EpisodicMemory(db_path=self.config.memory.sqlite_db_path)
        self.semantic_memory = semantic_memory or SemanticMemory()
        self.procedural_memory = procedural_memory or ProceduralMemory()
        self.cognition = cognition or CognitiveEngine(
            thinking_budget=self.config.cognition.default_thinking_budget
        )
        self.llm = llm or get_llm_provider(self.config)
        self.patcher = patcher or SurgicalPatcher(workspace_root=self.config.system.blackboard_repo_path)
        self.usage = TokenUsageTracker()

    def run(self, task: Task, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Template method wrapping execution with memory updates, turn logging, and pre-mortem analysis.
        """
        ctx = context or {}
        self.working_memory.add_entry(role=self.role, content=f"Starting execution on task '{task.title}'")

        # Execute agent specialized turn
        response = self.execute_turn(task, ctx)

        # Record tokens
        self.usage.add(
            prompt=response.tokens_used.prompt_tokens,
            candidate=response.tokens_used.candidate_tokens,
            thinking=response.tokens_used.thinking_tokens
        )

        # Log event in episodic memory
        self.episodic_memory.record_event(
            session_id=ctx.get("session_id", "mas-default-session"),
            task_id=task.id,
            agent_role=self.role,
            event_type="AGENT_TURN_COMPLETED",
            payload={
                "status": response.status,
                "summary": response.summary,
                "artifacts": response.artifacts_produced,
                "tokens": response.tokens_used.model_dump()
            }
        )

        self.working_memory.add_entry(role=self.role, content=f"Completed turn: {response.summary}")
        return response

    @abstractmethod
    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        """Domain-specific logic implemented by each specialized agent role."""
        pass

    def think_and_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        thinking_budget: Optional[int] = None
    ) -> LLMResponse:
        """
        Invokes the live LLM with extended reasoning token budget and role system prompt.
        """
        model_name = self.config.models.roles.get(self.role.lower(), self.config.models.default_model)
        budget = thinking_budget or self.config.cognition.default_thinking_budget
        gen_config = LLMGenerationConfig(thinking_budget=budget)

        sys_p = system_prompt or f"You are {self.role}, operating in the {self.pod.value} pod. Uphold strict SOLID and Clean Code standards."
        return self.llm.generate(prompt=prompt, system_prompt=sys_p, model=model_name, config=gen_config)

    def think_and_generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        thinking_budget: Optional[int] = None
    ) -> tuple[T, LLMResponse]:
        """
        Invokes LLM with strict Pydantic structured output validation.
        """
        model_name = self.config.models.roles.get(self.role.lower(), self.config.models.default_model)
        budget = thinking_budget or self.config.cognition.default_thinking_budget
        gen_config = LLMGenerationConfig(thinking_budget=budget)

        sys_p = system_prompt or f"You are {self.role}, an elite software engineering agent in the {self.pod.value} pod."
        return self.llm.generate_structured(
            prompt=prompt,
            schema=schema,
            system_prompt=sys_p,
            model=model_name,
            config=gen_config
        )

    def apply_surgical_patch(
        self,
        file_path: str,
        search_block: str,
        replace_block: str
    ) -> PatchResult:
        """
        Applies an AST-verified surgical patch to an existing codebase file.
        """
        return self.patcher.apply_search_replace_block(
            file_path=file_path,
            search_block=search_block,
            replace_block=replace_block,
            verify_ast=True
        )

    def publish_artifact(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        content: str
    ) -> Artifact:
        """Convenience method to register a versioned artifact to the Blackboard."""
        return self.blackboard.register_artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            content=content,
            created_by=self.role
        )
