"""
Tier 4: Procedural Memory (Deterministic Tool & Skill Registry).
Stores rigid schemas and invocation handlers for tools, linters, sandboxes, and skills.
"""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    roles_allowed: List[str] = Field(default_factory=list)
    is_sandboxed: bool = True
    timeout_seconds: int = 30


class ProceduralMemory:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable[..., Any]] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters_schema: Optional[Dict[str, Any]] = None,
        roles_allowed: Optional[List[str]] = None,
        is_sandboxed: bool = True,
        timeout_seconds: int = 30
    ) -> None:
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters_schema=parameters_schema or {},
            roles_allowed=roles_allowed or ["*"],
            is_sandboxed=is_sandboxed,
            timeout_seconds=timeout_seconds
        )
        self._handlers[name] = handler

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools_for_role(self, role: str) -> List[ToolDefinition]:
        return [
            t for t in self._tools.values()
            if "*" in t.roles_allowed or role in t.roles_allowed
        ]

    def execute_tool(self, name: str, caller_role: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in Procedural Memory.")

        tool = self._tools[name]
        if "*" not in tool.roles_allowed and caller_role not in tool.roles_allowed:
            raise PermissionError(f"Role '{caller_role}' is not authorized to invoke tool '{name}'.")

        handler = self._handlers[name]
        return handler(**kwargs)
