"""
Autonomous ReAct Multi-Turn Tool Execution Engine for MAS.
Powers iterative Observation-Action loops for software engineering agents with
deterministic tool schemas, AST verification gates, and sandbox isolation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from mas.core.blackboard import ArtifactBlackboard
from mas.core.llm import BaseLLMProvider, LLMGenerationConfig
from mas.tools.linter import DeterministicLinter
from mas.tools.patcher import SurgicalPatcher
from mas.tools.sandbox import SubprocessSandbox, get_sandbox_runner

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ReActTurn(BaseModel):
    turn_index: int
    thought: str
    tool_call: Optional[ToolCall] = None
    observation: str
    finish_summary: Optional[str] = None


class ReActResult(BaseModel):
    success: bool
    final_summary: str
    artifacts_produced: List[str] = Field(default_factory=list)
    turns: List[ReActTurn] = Field(default_factory=list)
    total_prompt_tokens: int = 0
    total_candidate_tokens: int = 0
    total_thinking_tokens: int = 0


class ReActToolbox:
    """
    Standard suite of secured engineering tools accessible to MAS autonomous agents.
    """

    def __init__(
        self,
        workspace_root: str = ".",
        blackboard: Optional[ArtifactBlackboard] = None,
        sandbox: Optional[SubprocessSandbox] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.blackboard = blackboard or ArtifactBlackboard(repo_path=str(self.workspace_root))
        self.sandbox = sandbox or get_sandbox_runner(workspace_root=str(self.workspace_root))
        self.patcher = SurgicalPatcher(workspace_root=str(self.workspace_root))
        self.linter = DeterministicLinter()

    def _resolve_safe_path(self, relative_path: str) -> Path:
        resolved = (self.workspace_root / relative_path).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Security error: path '{relative_path}' traverses outside workspace."
            )
        return resolved

    def read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists() or not safe_path.is_file():
            return f"Error: File '{path}' does not exist."

        try:
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            s = max(1, start_line or 1)
            e = min(len(lines), end_line or len(lines))
            selected = lines[s - 1 : e]
            return "".join(selected)
        except Exception as exc:
            return f"Error reading file '{path}': {str(exc)}"

    def write_file(self, path: str, content: str) -> str:
        safe_path = self._resolve_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Success: Wrote {len(content)} characters to '{path}'."
        except Exception as exc:
            return f"Error writing file '{path}': {str(exc)}"

    def apply_surgical_patch(self, path: str, search_block: str, replace_block: str) -> str:
        try:
            res = self.patcher.apply_search_replace_block(
                file_path=path,
                search_block=search_block,
                replace_block=replace_block,
                verify_ast=True,
            )
            if res.success:
                return f"Success: Applied patch to '{path}' (Lines {res.applied_line_range})."
            return f"Patch failed: {res.error_message}"
        except Exception as exc:
            return f"Error applying patch to '{path}': {str(exc)}"

    def ast_syntax_check(self, path: str) -> str:
        safe_path = self._resolve_safe_path(path)
        if not safe_path.exists():
            return f"Error: File '{path}' does not exist for AST check."

        res = self.linter.check_syntax_auto(str(safe_path))
        if res.passed:
            return f"AST Clean: File '{path}' passed syntax verification ({res.tool_name})."
        errs = [f"Line {e.line_number}: {e.message}" for e in res.issues]
        return f"AST Syntax Errors in '{path}' ({res.tool_name}):\n" + "\n".join(errs)

    def run_sandboxed_command(self, command: str, timeout: Optional[int] = None) -> str:
        parts = command.strip().split()
        if not parts:
            return "Error: Empty command string."

        try:
            res = self.sandbox.execute(parts, timeout=timeout or 35)
            out = res.stdout.strip()
            err = res.stderr.strip()
            status = f"Exit code: {res.exit_code} (Duration: {res.duration_seconds:.2f}s)"
            body = []
            if out:
                body.append(f"STDOUT:\n{out[:1200]}")
            if err:
                body.append(f"STDERR:\n{err[:1200]}")
            return f"{status}\n" + "\n".join(body)
        except Exception as exc:
            return f"Sandbox execution blocked: {str(exc)}"

    def query_blackboard(self, artifact_type: Optional[str] = None) -> str:
        artifacts = self.blackboard.list_artifacts()
        if not artifacts:
            return "Blackboard is currently empty. No artifacts committed yet."

        filtered = artifacts
        if artifact_type:
            filtered = [a for a in artifacts if a.type.value.lower() == artifact_type.lower()]

        items = []
        for a in filtered[:8]:
            snippet = a.content[:150].replace("\n", " ")
            items.append(
                f"- ID: {a.id} | Type: {a.type.value} | Name: {a.name} | Path: {a.path}\n  Snippet: {snippet}..."
            )
        return "Blackboard Artifacts:\n" + "\n".join(items)

    def list_directory(self, dir_path: str = ".") -> str:
        safe_path = self._resolve_safe_path(dir_path)
        if not safe_path.exists() or not safe_path.is_dir():
            return f"Error: Directory '{dir_path}' does not exist."

        entries = []
        try:
            for item in sorted(safe_path.iterdir()):
                rel = item.relative_to(self.workspace_root)
                tag = "[DIR]" if item.is_dir() else f"[{item.stat().st_size}B]"
                entries.append(f"{tag} {rel.as_posix()}")
            return "\n".join(entries[:40])
        except Exception as exc:
            return f"Error listing directory '{dir_path}': {str(exc)}"

    def get_tool_definitions(self) -> List[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Reads content from a workspace file with optional line boundaries.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative file path from workspace root.",
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Optional 1-based start line.",
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "Optional 1-based end line.",
                        },
                    },
                    "required": ["path"],
                },
            ),
            ToolDefinition(
                name="write_file",
                description="Writes or overwrites a file with new content inside the workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path."},
                        "content": {"type": "string", "description": "Full file content to write."},
                    },
                    "required": ["path", "content"],
                },
            ),
            ToolDefinition(
                name="apply_surgical_patch",
                description="Applies an AST-verified search and replace block to modify an existing file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Target file path."},
                        "search_block": {"type": "string", "description": "Exact text to find."},
                        "replace_block": {"type": "string", "description": "Replacement text."},
                    },
                    "required": ["path", "search_block", "replace_block"],
                },
            ),
            ToolDefinition(
                name="ast_syntax_check",
                description="Verifies syntax correctness of a Python or TypeScript file using AST parsing.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path."},
                    },
                    "required": ["path"],
                },
            ),
            ToolDefinition(
                name="run_sandboxed_command",
                description="Executes a CLI test, build, or linter command in the isolated sandbox.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Whitelisted command to execute, e.g. 'pytest tests/' or 'ruff check .'",
                        },
                    },
                    "required": ["command"],
                },
            ),
            ToolDefinition(
                name="query_blackboard",
                description="Retrieves locked PRD, ADR, API Spec, and Schema artifacts from the Blackboard.",
                parameters={
                    "type": "object",
                    "properties": {
                        "artifact_type": {
                            "type": "string",
                            "description": "Optional type filter (e.g. API_SPEC, PRD, ADR).",
                        },
                    },
                },
            ),
            ToolDefinition(
                name="list_directory",
                description="Lists directory files and structure.",
                parameters={
                    "type": "object",
                    "properties": {
                        "dir_path": {
                            "type": "string",
                            "description": "Relative directory path (defaults to '.').",
                        },
                    },
                },
            ),
            ToolDefinition(
                name="finish",
                description="Finishes the task once all goals and verified code files are complete.",
                parameters={
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Detailed explanation of what was achieved.",
                        },
                        "artifacts_produced": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file paths created or updated.",
                        },
                    },
                    "required": ["summary"],
                },
            ),
        ]


class AutonomousReActEngine:
    """
    Executes an iterative, multi-turn ReAct reasoning loop.
    Supports live LLM invocation, schema-based action parsing, AST verification, and termination.
    """

    def __init__(
        self,
        llm: BaseLLMProvider,
        toolbox: ReActToolbox,
        max_turns: int = 5,
        model_name: Optional[str] = None,
    ):
        self.llm = llm
        self.toolbox = toolbox
        self.max_turns = max_turns
        self.model_name = model_name

    def _build_system_prompt(self, role: str, objective: str) -> str:
        tools = self.toolbox.get_tool_definitions()
        tool_desc = "\n".join(
            [f"- {t.name}: {t.description}\n  Schema: {json.dumps(t.parameters)}" for t in tools]
        )

        return (
            f"You are {role}, an elite software engineering agent operating in the MAS Multi-Agent System.\n"
            f"Your current objective: {objective}\n\n"
            f"You operate in a strict Observation-Action ReAct loop. In each turn, output:\n"
            f"Thought: <Your reasoning about what to do next>\n"
            f"Action: <Tool name>\n"
            f"Action Input: <JSON object containing arguments matching the tool schema>\n\n"
            f"Available Tools:\n{tool_desc}\n\n"
            f"CRITICAL RULES:\n"
            f"1. When code changes are made, run 'ast_syntax_check' to ensure syntax is 100% valid before finishing.\n"
            f"2. When your task is complete, call the 'finish' tool with your summary and artifacts.\n"
            f"3. Always keep Action Input as strictly valid JSON.\n"
        )

    def _parse_action_response(self, text: str) -> Tuple[str, Optional[ToolCall], Optional[str]]:
        thought = ""
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()

        action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", text, re.IGNORECASE)
        if not action_match:
            return thought or text.strip(), None, None

        action_name = action_match.group(1).strip()
        input_match = re.search(r"Action Input:\s*(\{.*\}|\[.*\])", text, re.DOTALL | re.IGNORECASE)

        args: Dict[str, Any] = {}
        if input_match:
            try:
                args = json.loads(input_match.group(1).strip())
            except Exception:
                # Attempt to extract json block
                raw_json = input_match.group(1).strip()
                cleaned = re.sub(r"```json\s*", "", raw_json)
                cleaned = re.sub(r"```\s*$", "", cleaned)
                try:
                    args = json.loads(cleaned)
                except Exception:
                    args = {"raw_input": raw_json}

        if action_name.lower() == "finish":
            summary = args.get("summary", thought or "Task completed.")
            return thought, ToolCall(name="finish", arguments=args), summary

        return thought, ToolCall(name=action_name, arguments=args), None

    def execute_loop(
        self,
        role: str,
        task_title: str,
        task_description: str,
        initial_context: Optional[str] = None,
    ) -> ReActResult:
        system_prompt = self._build_system_prompt(role, f"{task_title}: {task_description}")
        conversation_history: List[str] = []

        if initial_context:
            conversation_history.append(f"Context from previous stages:\n{initial_context}\n")

        conversation_history.append(
            f"Task: {task_title}\nDescription: {task_description}\n"
            f"Begin by inspecting relevant artifacts or existing files, then implement and verify."
        )

        turns_executed: List[ReActTurn] = []
        p_tok = 0
        c_tok = 0
        t_tok = 0
        artifacts: List[str] = []

        for turn_idx in range(1, self.max_turns + 1):
            prompt = "\n\n".join(conversation_history)
            config = LLMGenerationConfig(temperature=0.1, thinking_budget=2048)

            try:
                resp = self.llm.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=self.model_name,
                    config=config,
                )
            except Exception as exc:
                logger.warning(f"ReAct LLM turn {turn_idx} failed: {exc}")
                break

            p_tok += resp.prompt_tokens
            c_tok += resp.candidate_tokens
            t_tok += resp.thinking_tokens

            thought, tool_call, finish_summary = self._parse_action_response(resp.text)

            if finish_summary or (tool_call and tool_call.name.lower() == "finish"):
                produced = (
                    tool_call.arguments.get("artifacts_produced", []) if tool_call else []
                ) or artifacts
                turns_executed.append(
                    ReActTurn(
                        turn_index=turn_idx,
                        thought=thought,
                        tool_call=tool_call,
                        observation="Task successfully finished.",
                        finish_summary=finish_summary or "Task finished.",
                    )
                )
                return ReActResult(
                    success=True,
                    final_summary=finish_summary or "Autonomous task completed.",
                    artifacts_produced=produced,
                    turns=turns_executed,
                    total_prompt_tokens=p_tok,
                    total_candidate_tokens=c_tok,
                    total_thinking_tokens=t_tok,
                )

            if not tool_call:
                # No explicit action returned, simulate next step
                observation = (
                    "Observation: Please specify an Action and valid Action Input to proceed."
                )
            else:
                # Execute tool
                observation = self._dispatch_tool(tool_call)
                if tool_call.name == "write_file":
                    p = tool_call.arguments.get("path")
                    if p and p not in artifacts:
                        artifacts.append(p)

            turns_executed.append(
                ReActTurn(
                    turn_index=turn_idx,
                    thought=thought,
                    tool_call=tool_call,
                    observation=observation,
                )
            )

            conversation_history.append(
                f"Thought: {thought}\n"
                f"Action: {tool_call.name if tool_call else 'None'}\n"
                f"Action Input: {json.dumps(tool_call.arguments) if tool_call else '{}'}\n"
                f"Observation: {observation}\n"
            )

        # Finished max turns
        return ReActResult(
            success=len(artifacts) > 0,
            final_summary=f"ReAct loop executed {len(turns_executed)} turns.",
            artifacts_produced=artifacts,
            turns=turns_executed,
            total_prompt_tokens=p_tok,
            total_candidate_tokens=c_tok,
            total_thinking_tokens=t_tok,
        )

    def _dispatch_tool(self, tool_call: ToolCall) -> str:
        name = tool_call.name.lower()
        args = tool_call.arguments

        try:
            if name == "read_file":
                return self.toolbox.read_file(
                    path=args.get("path", ""),
                    start_line=args.get("start_line"),
                    end_line=args.get("end_line"),
                )
            elif name == "write_file":
                return self.toolbox.write_file(
                    path=args.get("path", ""),
                    content=args.get("content", ""),
                )
            elif name == "apply_surgical_patch":
                return self.toolbox.apply_surgical_patch(
                    path=args.get("path", ""),
                    search_block=args.get("search_block", ""),
                    replace_block=args.get("replace_block", ""),
                )
            elif name == "ast_syntax_check":
                return self.toolbox.ast_syntax_check(path=args.get("path", ""))
            elif name == "run_sandboxed_command":
                return self.toolbox.run_sandboxed_command(
                    command=args.get("command", ""),
                    timeout=args.get("timeout"),
                )
            elif name == "query_blackboard":
                return self.toolbox.query_blackboard(artifact_type=args.get("artifact_type"))
            elif name == "list_directory":
                return self.toolbox.list_directory(dir_path=args.get("dir_path", "."))
            else:
                return f"Error: Tool '{name}' is not recognized."
        except Exception as exc:
            return f"Tool execution exception: {str(exc)}"
