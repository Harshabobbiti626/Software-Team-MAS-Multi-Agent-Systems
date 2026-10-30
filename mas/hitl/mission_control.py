"""
Interactive Mission Control & Situational Awareness Terminal UI for MAS.
Renders real-time pod statuses, token burn velocity, blackboard artifacts,
and interactive Human-in-the-Loop (HITL) approval gateways.
"""

import sys
from typing import Any, Dict, List, Optional

from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.state import Task
from mas.hitl.gates import GateDecision, GateLevel


class MissionControlConsole:
    def __init__(self, use_color: bool = True):
        self.use_color = use_color and sys.stdout.isatty()

    def _c(self, text: str, color_code: str) -> str:
        if not self.use_color:
            return text
        return f"\033[{color_code}m{text}\033[0m"

    def banner(self, task: Task, circuit_breaker: Optional[CircuitBreaker] = None) -> str:
        turns = circuit_breaker.total_turns if circuit_breaker else 0
        prompt_t = circuit_breaker.prompt_tokens if circuit_breaker else 0
        cand_t = circuit_breaker.candidate_tokens if circuit_breaker else 0
        think_t = circuit_breaker.thinking_tokens if circuit_breaker else 0
        total_tokens = prompt_t + cand_t + think_t
        tripped = circuit_breaker.is_tripped() if circuit_breaker else False

        status_str = (
            self._c("TRIPPED (HALTED)", "31;1") if tripped else self._c("ACTIVE (NORMAL)", "32;1")
        )

        header = [
            "╔════════════════════════════════════════════════════════════════════════════════╗",
            f"║  🚀 {self._c('MAS MULTI-AGENT MISSION CONTROL', '36;1'):<78} ║",
            "╠════════════════════════════════════════════════════════════════════════════════╣",
            f"║  Mission: {self._c(task.title[:55], '1'):<78} ║",
            f"║  Task ID: {task.id:<18} Assigned Pod: {task.assigned_pod.value:<18} Status: {status_str:<22} ║",
            f"║  Turns: {turns:<6} Tokens: {total_tokens:,} (Prompt: {prompt_t:,} | Cand: {cand_t:,} | Think: {think_t:,}) ║",
            "╚════════════════════════════════════════════════════════════════════════════════╝",
        ]
        return "\n".join(header)

    def render_pod_matrix(
        self, active_pods: List[str], completed_results: Optional[Dict[str, Any]] = None
    ) -> str:
        completed = completed_results or {}
        pods = [
            ("Data Pod", ["DatabaseArchitectAgent", "DataEngineerAgent"]),
            ("Backend & AI Pod", ["BackendEngineerAgent", "AIMLEngineerAgent"]),
            ("Frontend Pod", ["UIUXDesignerAgent", "FrontendEngineerAgent"]),
            ("Cloud & Platform Pod", ["CloudEngineerAgent", "DevOpsSREAgent"]),
            ("Governance & QA", ["QASDETAgent", "CodeReviewerAgent", "AppSecAgent"]),
        ]

        lines = ["\n📊 [SPECIALIZED ENGINEERING POD STATUS]"]
        for pod_name, roles in pods:
            statuses = []
            for r in roles:
                if r in completed:
                    st = completed[r].status if hasattr(completed[r], "status") else "DONE"
                    color = "32" if st == "SUCCESS" else "31"
                    statuses.append(f"{r}: {self._c(st, color)}")
                elif r in active_pods:
                    statuses.append(f"{r}: {self._c('RUNNING', '33;1')}")
                else:
                    statuses.append(f"{r}: {self._c('IDLE', '90')}")
            lines.append(f"  • {self._c(pod_name, '1')}: {' | '.join(statuses)}")
        return "\n".join(lines)

    def render_artifact_ledger(self, blackboard: ArtifactBlackboard) -> str:
        artifacts = blackboard.list_artifacts()
        if not artifacts:
            return "\n📦 [ARTIFACT BLACKBOARD]: No artifacts registered yet."

        lines = ["\n📦 [ARTIFACT BLACKBOARD (GIT-BACKED LEDGER)]"]
        lines.append(
            "  ┌───────────────────────┬──────────────┬─────────┬───────────────────────────┐"
        )
        lines.append(
            "  │ Artifact ID           │ Type         │ Version │ Created By                │"
        )
        lines.append(
            "  ├───────────────────────┼──────────────┼─────────┼───────────────────────────┤"
        )
        for a in artifacts[:8]:
            lines.append(
                f"  │ {a.id:<21} │ {a.type.value:<12} │ v{a.version:<6} │ {a.created_by:<25} │"
            )
        lines.append(
            "  └───────────────────────┴──────────────┴─────────┴───────────────────────────┘"
        )
        return "\n".join(lines)

    def prompt_gate_decision(
        self, gate: GateLevel, task_id: str, context: Optional[Dict[str, Any]] = None
    ) -> GateDecision:
        ctx = context or {}
        summary = ctx.get("summary", "Approval request for next stage transition.")
        blast_radius = ctx.get("blast_radius", "")
        cost_impact = ctx.get("cost_impact", "")

        print("\n" + "!" * 80)
        print(f"🛑 [HUMAN-IN-THE-LOOP APPROVAL REQUIRED]: {self._c(gate.value, '33;1')}")
        print(f"   Task: {task_id}")
        print(f"   Decision Summary: {summary}")
        if blast_radius:
            print(f"   Blast Radius: {blast_radius}")
        if cost_impact:
            print(f"   Cost Impact: {cost_impact}")
        print("!" * 80)

        while True:
            try:
                choice = (
                    input("\n👉 Enter decision [A]pprove / [R]eject / [M]odify (default: Approve): ")
                    .strip()
                    .upper()
                )
                if choice in ("A", "APPROVE", ""):
                    return GateDecision(
                        gate=gate,
                        task_id=task_id,
                        decision="APPROVED",
                        reviewer="HumanOperator",
                        rationale="Approved via interactive mission control",
                    )
                elif choice in ("R", "REJECT"):
                    reason = (
                        input("Enter rejection reason: ").strip() or "Rejected by human operator"
                    )
                    return GateDecision(
                        gate=gate,
                        task_id=task_id,
                        decision="REJECTED",
                        reviewer="HumanOperator",
                        rationale=reason,
                    )
                elif choice in ("M", "MODIFY"):
                    comments = (
                        input("Enter revision requests / constraints: ").strip()
                        or "Requested modifications"
                    )
                    return GateDecision(
                        gate=gate,
                        task_id=task_id,
                        decision="REVISION_REQUESTED",
                        reviewer="HumanOperator",
                        rationale=comments,
                    )
                else:
                    print("Invalid input. Please enter A, R, or M.")
            except (KeyboardInterrupt, EOFError):
                return GateDecision(
                    gate=gate,
                    task_id=task_id,
                    decision="REJECTED",
                    reviewer="HumanOperator",
                    rationale="Interrupted by user",
                )
