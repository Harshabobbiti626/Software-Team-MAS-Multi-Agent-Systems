"""
MAS Orchestrator & State Machine Engine.
Coordinates Just-In-Time (JIT) pod activation, contract-first parallel dispatch,
closed-loop diagnostic remediation, and hierarchical workflow transitions.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.config import MASConfiguration, get_config
from mas.core.router import IntelligentRouter
from mas.core.state import (
    SubsystemClass,
    SystemState,
    Task,
    TaskPriority,
    TaskStatus,
    TestReport,
)


class MASOrchestrator:
    def __init__(
        self,
        config: Optional[MASConfiguration] = None,
        blackboard: Optional[ArtifactBlackboard] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.config = config or get_config()
        self.blackboard = blackboard or ArtifactBlackboard(repo_path=self.config.system.blackboard_repo_path)
        self.circuit_breaker = circuit_breaker or CircuitBreaker(self.config.limits)
        self.router = IntelligentRouter()
        self.state = SystemState(session_id="mas-session-001")

    def analyze_blast_radius(self, task_description: str) -> SubsystemClass:
        """
        Just-In-Time (JIT) scope analyzer: classifies task into bounded subsystem pods.
        Dormant pods are never awakened.
        """
        desc = task_description.lower()
        has_fe = any(k in desc for k in ["ui", "frontend", "css", "react", "view", "page", "button"])
        has_be = any(k in desc for k in ["api", "backend", "service", "microservice", "endpoint"])
        has_data = any(k in desc for k in ["sql", "database", "migration", "schema", "postgres", "table"])
        has_cloud = any(k in desc for k in ["terraform", "docker", "k8s", "kubernetes", "helm", "aws", "gcp"])

        # Check multi-subsystem / full-system indicators first
        subsystem_count = sum([has_fe, has_be, has_data, has_cloud])
        if subsystem_count > 1 or "system" in desc or "full" in desc or "end-to-end" in desc:
            return SubsystemClass.FULL_SYSTEM

        if has_data:
            return SubsystemClass.DATA
        if has_fe:
            return SubsystemClass.FRONTEND
        if has_cloud:
            return SubsystemClass.CLOUD_DEVOPS
        if has_be:
            return SubsystemClass.BACKEND

        return SubsystemClass.FULL_SYSTEM

    def determine_active_pods(self, target_pod: SubsystemClass) -> List[str]:
        """
        Returns only the exact agent roles needed for the given subsystem.
        """
        mapping = {
            SubsystemClass.DATA: ["DatabaseArchitectAgent", "DataEngineerAgent", "QASDETAgent"],
            SubsystemClass.FRONTEND: ["UIUXDesignerAgent", "FrontendEngineerAgent", "QASDETAgent"],
            SubsystemClass.BACKEND: ["BackendEngineerAgent", "AIMLEngineerAgent", "QASDETAgent"],
            SubsystemClass.CLOUD_DEVOPS: ["CloudEngineerAgent", "DevOpsSREAgent", "QASDETAgent"],
            SubsystemClass.SECURITY: ["AppSecAgent", "CodeReviewerAgent"],
            SubsystemClass.QUALITY: ["QASDETAgent", "CodeReviewerAgent"],
            SubsystemClass.DOCUMENTATION: ["TechnicalWriterAgent"],
            SubsystemClass.FULL_SYSTEM: [
                "BusinessSponsorAgent", "ProductManagerAgent", "DomainSMEAgent",
                "SystemArchitectAgent", "TechLeadAgent",
                "DatabaseArchitectAgent", "BackendEngineerAgent", "FrontendEngineerAgent",
                "CloudEngineerAgent", "DevOpsSREAgent", "QASDETAgent",
                "CodeReviewerAgent", "AppSecAgent", "TechnicalWriterAgent"
            ]
        }
        return mapping.get(target_pod, mapping[SubsystemClass.FULL_SYSTEM])

    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.HIGH,
        business_goal_id: str = "GOAL-001"
    ) -> Task:
        subsystem = self.analyze_blast_radius(description)
        task = Task(
            id=task_id,
            title=title,
            description=description,
            business_goal_id=business_goal_id,
            assigned_pod=subsystem,
            priority=priority,
            status=TaskStatus.PENDING
        )
        self.state.current_task = task
        self.state.active_pods = self.determine_active_pods(subsystem)
        return task

    def advance_stage(self, new_status: TaskStatus) -> None:
        if not self.state.current_task:
            raise ValueError("No active task to advance")
        self.state.current_task.status = new_status
        self.circuit_breaker.record_turn("Orchestrator")

    def execute_parallel_pods(
        self,
        task: Task,
        pod_agents: List[Any],
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Executes engineering pods concurrently against compiled contracts (api-spec.yaml / schema.sql).
        Cuts execution time significantly by building backend, frontend, cloud, and DBA in parallel.
        """
        results: Dict[str, Any] = {}

        def _run_agent(agent: Any):
            return agent.role, agent.run(task)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_agent = {executor.submit(_run_agent, agent): agent for agent in pod_agents}
            for future in as_completed(future_to_agent):
                role, response = future.result()
                results[role] = response
                self.circuit_breaker.record_turn(role)
                self.circuit_breaker.record_tokens(
                    response.tokens_used.prompt_tokens,
                    response.tokens_used.candidate_tokens,
                    response.tokens_used.thinking_tokens
                )

        return results

    def trigger_remediation_loop(
        self,
        task: Task,
        test_report: TestReport,
        agent_roster: Dict[str, Any],
        qa_agent: Any,
        max_remediation_attempts: int = 2
    ) -> bool:
        """
        Closed-loop self-healing mechanism:
        When a test breaks, attributes responsibility via IntelligentRouter,
        dispatches a scoped remediation ticket to the culprit agent, and re-verifies.
        """
        for attempt in range(1, max_remediation_attempts + 1):
            if test_report.passed_all:
                self.circuit_breaker.record_success()
                return True

            ticket = self.router.triage_failure(
                task_id=task.id,
                test_report=test_report,
                error_output=test_report.stderr
            )

            self.circuit_breaker.record_failure(ticket.root_cause_summary)

            target_agent = agent_roster.get(ticket.assignee_role)
            if target_agent and hasattr(target_agent, "apply_surgical_patch"):
                # Apply remediation patch or re-generate
                target_agent.execute_turn(task, context={"remediation_ticket": ticket.model_dump()})

            # Re-verify with QA
            qa_res = qa_agent.run(task)
            self.circuit_breaker.record_turn(qa_agent.role)

            report_art = self.blackboard.get_artifact(f"test-report-{task.id}")
            if (report_art and "PASSED" in report_art.content) or qa_res.status == "SUCCESS":
                self.circuit_breaker.record_success()
                return True

        return False
