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
from mas.core.react_engine import AutonomousReActEngine, ReActResult, ReActToolbox
from mas.core.state import (
    Artifact,
    ArtifactType,
    SubsystemClass,
    Task,
    TestReport,
    TokenUsageTracker,
)
from mas.memory.code_graph import CodeKnowledgeGraph
from mas.memory.episodic import EpisodicMemory
from mas.memory.procedural import ProceduralMemory
from mas.memory.semantic import SemanticMemory
from mas.memory.working import WorkingMemory
from mas.tools.linter import DeterministicLinter
from mas.tools.patcher import PatchResult, SurgicalPatcher
from mas.tools.sandbox import SandboxResult, get_sandbox_runner

T = TypeVar("T", bound=BaseModel)


class AgentResponse(BaseModel):
    agent_role: str
    status: str = "SUCCESS"  # "SUCCESS", "FAILED", "BLOCKED"
    summary: str
    artifacts_produced: List[str] = Field(default_factory=list)
    pre_mortem: Optional[PreMortemAnalysis] = None
    test_report: Optional[TestReport] = None
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
        patcher: Optional[SurgicalPatcher] = None,
        linter: Optional[DeterministicLinter] = None,
        code_graph: Optional[CodeKnowledgeGraph] = None,
    ):
        self.role = role
        self.pod = pod
        self.config = config or get_config()
        self.blackboard = blackboard or ArtifactBlackboard(
            repo_path=self.config.system.blackboard_repo_path
        )
        self.working_memory = working_memory or WorkingMemory(
            window_size=self.config.memory.working_memory_window,
            compaction_threshold=self.config.memory.compaction_threshold_tokens,
        )
        self.episodic_memory = episodic_memory or EpisodicMemory(
            db_path=self.config.memory.sqlite_db_path
        )
        self.semantic_memory = semantic_memory or SemanticMemory()
        self.procedural_memory = procedural_memory or ProceduralMemory()
        self.cognition = cognition or CognitiveEngine(
            thinking_budget=self.config.cognition.default_thinking_budget
        )
        self.llm = llm or get_llm_provider(self.config)
        self.patcher = patcher or SurgicalPatcher(
            workspace_root=self.config.system.blackboard_repo_path
        )
        self.linter = linter or DeterministicLinter()
        self.code_graph = code_graph or CodeKnowledgeGraph(
            workspace_root=self.config.system.blackboard_repo_path
        )
        self.usage = TokenUsageTracker()

    def run(self, task: Task, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Template method wrapping execution with memory updates, turn logging, and pre-mortem analysis.
        """
        ctx = context or {}
        self.working_memory.add_entry(
            role=self.role, content=f"Starting execution on task '{task.title}'"
        )

        # Execute agent specialized turn
        response = self.execute_turn(task, ctx)

        # Record tokens
        self.usage.add(
            prompt=response.tokens_used.prompt_tokens,
            candidate=response.tokens_used.candidate_tokens,
            thinking=response.tokens_used.thinking_tokens,
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
                "tokens": response.tokens_used.model_dump(),
            },
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
        thinking_budget: Optional[int] = None,
    ) -> LLMResponse:
        """
        Invokes the live LLM with extended reasoning token budget and role system prompt.
        Automatically updates live token consumption.
        """
        model_name = self.config.models.roles.get(
            self.role.lower(), self.config.models.default_model
        )
        budget = thinking_budget or self.config.cognition.default_thinking_budget
        gen_config = LLMGenerationConfig(thinking_budget=budget)

        sys_p = (
            system_prompt
            or f"You are {self.role}, operating in the {self.pod.value} pod. Uphold strict SOLID and Clean Code standards."
        )
        resp = self.llm.generate(
            prompt=prompt, system_prompt=sys_p, model=model_name, config=gen_config
        )
        self.usage.add(
            prompt=resp.prompt_tokens,
            candidate=resp.candidate_tokens,
            thinking=resp.thinking_tokens,
        )
        return resp

    def think_and_generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        thinking_budget: Optional[int] = None,
    ) -> tuple[T, LLMResponse]:
        """
        Invokes LLM with strict Pydantic structured output validation.
        Automatically updates live token consumption.
        """
        model_name = self.config.models.roles.get(
            self.role.lower(), self.config.models.default_model
        )
        budget = thinking_budget or self.config.cognition.default_thinking_budget
        gen_config = LLMGenerationConfig(thinking_budget=budget)

        sys_p = (
            system_prompt
            or f"You are {self.role}, an elite software engineering agent in the {self.pod.value} pod."
        )
        obj, resp = self.llm.generate_structured(
            prompt=prompt, schema=schema, system_prompt=sys_p, model=model_name, config=gen_config
        )
        self.usage.add(
            prompt=resp.prompt_tokens,
            candidate=resp.candidate_tokens,
            thinking=resp.thinking_tokens,
        )
        return obj, resp

    def apply_surgical_patch(
        self, file_path: str, search_block: str, replace_block: str
    ) -> PatchResult:
        """
        Applies an AST-verified surgical patch to an existing codebase file.
        """
        return self.patcher.apply_search_replace_block(
            file_path=file_path,
            search_block=search_block,
            replace_block=replace_block,
            verify_ast=True,
        )

    def execute_codeact_loop(
        self,
        test_command: List[str],
        max_attempts: int = 3,
        auto_repair_callback: Optional[Any] = None,
    ) -> SandboxResult:
        """
        Interactive CodeAct execution & self-debugging loop.
        Executes a test/build in the sandbox; if failures occur, analyzes error tracebacks,
        applies surgical patches, and re-runs until green or turn limits are hit.
        """
        sandbox = get_sandbox_runner(workspace_root=self.config.system.blackboard_repo_path)
        result = SandboxResult(
            command=" ".join(test_command),
            exit_code=-1,
            stdout="",
            stderr="No execution attempts made.",
            duration_seconds=0.0,
        )

        for attempt in range(1, max_attempts + 1):
            result = sandbox.execute(test_command, timeout=45)
            if result.exit_code == 0:
                self.working_memory.add_entry(
                    role=self.role,
                    content=f"CodeAct command passed on attempt {attempt}: {' '.join(test_command)}",
                )
                return result

            # Failure encountered -> log and reflect
            error_msg = result.stderr if result.stderr else result.stdout
            self.working_memory.add_entry(
                role=self.role,
                content=f"CodeAct attempt {attempt} failed (exit {result.exit_code}). Error: {error_msg[:300]}",
            )

            if auto_repair_callback:
                repair_patch = auto_repair_callback(result, attempt)
                if repair_patch:
                    file_p, s_block, r_block = repair_patch
                    patch_res = self.apply_surgical_patch(file_p, s_block, r_block)
                    if not patch_res.success:
                        self.working_memory.add_entry(
                            role=self.role, content=f"Patch failed: {patch_res.error_message}"
                        )
            else:
                # Default LLM-assisted reflection
                reflection = self.cognition.reflect_on_outcome(
                    step_goal=f"Execute {' '.join(test_command)}",
                    expected="Process exit code 0",
                    actual=error_msg[:200],
                )
                self.working_memory.add_entry(
                    role=self.role,
                    content=f"Cognitive Reflection: {reflection.discrepancy_explanation}",
                )

        return result

    def execute_react_code_generation(
        self,
        task: Task,
        target_file: str,
        initial_prompt: str,
        system_prompt: Optional[str] = None,
        max_attempts: int = 3,
    ) -> tuple[str, bool]:
        """
        Autonomous ReAct generation loop:
        1. Contextualizes with CodeKnowledgeGraph.
        2. Generates candidate code with live LLM extended thinking.
        3. Validates syntax via DeterministicLinter AST analysis.
        4. In case of syntax error, feeds trace back to LLM for self-correction.
        5. Returns (verified_code, is_valid).
        """
        # Context gathering from code graph
        context_slice = ""
        try:
            tokens = [w for w in task.title.split() if len(w) > 3]
            matched_symbols = []
            for tok in tokens[:3]:
                syms = self.code_graph.find_symbol(tok)
                if syms:
                    matched_symbols.append(tok)
            if matched_symbols:
                slice_content = self.code_graph.get_context_slice(matched_symbols, max_lines=60)
                if slice_content:
                    context_slice = f"\n### Relevant Existing Codebase Context:\n{slice_content}\n"
        except Exception:
            pass

        current_prompt = f"{initial_prompt}\n{context_slice}" if context_slice else initial_prompt
        last_code = ""

        for attempt in range(1, max_attempts + 1):
            llm_resp = self.think_and_generate(
                prompt=current_prompt,
                system_prompt=system_prompt,
            )
            code_candidate = llm_resp.text.strip()
            # Clean markdown code blocks if present (polyglot)
            if code_candidate.startswith("```"):
                # strip opening tag like ```python, ```typescript, ```sql, etc.
                first_newline = code_candidate.find("\n")
                if first_newline != -1:
                    code_candidate = code_candidate[first_newline + 1 :]
                else:
                    code_candidate = code_candidate[3:]
            if code_candidate.endswith("```"):
                code_candidate = code_candidate[:-3]
            code_candidate = code_candidate.strip()
            last_code = code_candidate

            # Polyglot Syntax Verification Gate
            lint_res = self.linter.check_syntax_auto(target_file, code_candidate)
            if lint_res.passed:
                self.working_memory.add_entry(
                    role=self.role,
                    content=f"ReAct code generation succeeded on attempt {attempt} for {target_file} ({lint_res.tool_name}).",
                )
                return code_candidate, True

            # Self-healing feedback loop
            error_details = (
                lint_res.issues[0].message
                if lint_res.issues
                else (lint_res.raw_output or "SyntaxError: invalid syntax")
            )
            self.working_memory.add_entry(
                role=self.role,
                content=f"ReAct attempt {attempt} failed syntax: {error_details}. Prompting self-repair.",
            )
            current_prompt = (
                f"The generated content for '{target_file}' failed syntax verification ({lint_res.tool_name}).\n"
                f"Syntax Error: {error_details}\n"
                f"Failing Content:\n```\n{code_candidate}\n```\n"
                f"Fix all syntax issues and return the complete, valid code without placeholder comments."
            )

        return last_code, False

    def publish_artifact(
        self,
        artifact_id: str,
        artifact_type: ArtifactType,
        name: str,
        content: str,
        path: Optional[str] = None,
        commit_to_git: bool = True,
    ) -> Artifact:
        """Convenience method to register a versioned artifact to the Blackboard."""
        return self.blackboard.register_artifact(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            name=name,
            content=content,
            created_by=self.role,
            path=path,
            commit_to_git=commit_to_git,
        )

    def execute_react_mission_loop(
        self,
        task: Task,
        objective: str,
        max_turns: Optional[int] = None,
    ) -> ReActResult:
        """
        Executes a true multi-turn Observation-Action ReAct loop with full toolbox access.
        Enables agents to dynamically inspect, write, patch, verify AST, and run sandboxed tests.
        """
        toolbox = ReActToolbox(
            workspace_root=self.config.system.blackboard_repo_path,
            blackboard=self.blackboard,
        )
        engine = AutonomousReActEngine(
            llm=self.llm,
            toolbox=toolbox,
            max_turns=max_turns or self.config.limits.max_turns_per_agent,
            model_name=self.config.models.roles.get(
                self.role.lower(), self.config.models.default_model
            ),
        )
        res = engine.execute_loop(
            role=self.role,
            task_title=task.title,
            task_description=task.description,
            initial_context=objective,
        )
        self.usage.add(
            prompt=res.total_prompt_tokens,
            candidate=res.total_candidate_tokens,
            thinking=res.total_thinking_tokens,
        )
        return res
