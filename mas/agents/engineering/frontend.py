"""
Frontend Engineer Agent.
Implements client UI components, state stores, and user flows against mock and live API contracts.
"""

from typing import Any, Dict

from mas.agents.base import AgentResponse, BaseAgent
from mas.core.state import ArtifactType, SubsystemClass, Task, TokenUsageTracker


class FrontendEngineerAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__(role="FrontendEngineerAgent", pod=SubsystemClass.FRONTEND, **kwargs)

    def execute_turn(self, task: Task, context: Dict[str, Any]) -> AgentResponse:
        component_code = f"""/**
 * Provenance Header:
 * Task-ID: {task.id}
 * ADR-Ref: ADR-001
 * Author: FrontendEngineerAgent
 * Contract: api-spec.yaml
 */

import React, {{ useState }} from 'react';

interface ResourcePayload {{
  name: string;
  category: string;
}}

export const ResourceView: React.FC = () => {{
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {{
    e.preventDefault();
    if (!name || !category) return;
    setStatus('SUBMITTING');
    try {{
      const res = await fetch('/api/v1/resource', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ name, category }})
      }});
      if (res.ok) {{
        setStatus('SUCCESS');
      }} else {{
        setStatus('ERROR');
      }}
    }} catch {{
      setStatus('ERROR');
    }}
  }};

  return (
    <div className="p-4 border rounded shadow-sm">
      <h2 className="text-xl font-bold">{task.title}</h2>
      <form onSubmit={{handleSubmit}} className="space-y-4">
        <input 
          aria-label="resource-name" 
          value={{name}} 
          onChange={{(e) => setName(e.target.value)}} 
          placeholder="Resource Name" 
          className="border p-2 w-full"
        />
        <input 
          aria-label="resource-category" 
          value={{category}} 
          onChange={{(e) => setCategory(e.target.value)}} 
          placeholder="Category" 
          className="border p-2 w-full"
        />
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
          Create Resource
        </button>
      </form>
      {{status && <div data-testid="status-indicator">{{status}}</div>}}
    </div>
  );
}};
"""

        artifact = self.publish_artifact(
            artifact_id=f"frontend-code-{task.id}",
            artifact_type=ArtifactType.CODE_PATCH,
            name="ResourceView.tsx",
            content=component_code,
        )

        tokens = TokenUsageTracker(prompt_tokens=950, candidate_tokens=550, thinking_tokens=700)
        tokens.total_tokens = 2200

        return AgentResponse(
            agent_role=self.role,
            status="SUCCESS",
            summary="Created React component ResourceView.tsx wired to api-spec.yaml endpoints.",
            artifacts_produced=[artifact.id],
            tokens_used=tokens,
        )
