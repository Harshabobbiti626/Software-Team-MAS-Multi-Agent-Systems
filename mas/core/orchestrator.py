"""
MAS Orchestrator & State Machine Engine.
Coordinates Just-In-Time (JIT) pod activation, contract-first parallel dispatch,
and hierarchical workflow transitions.
"""

from typing import Dict, List, Optional
from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.config import MASConfiguration, get_config
from mas.core.state import (
    ArtifactType,
    SubsystemClass,
    SystemState,
    Task,
    TaskPriority,
    TaskStatus,
)
from mas.core.router import IntelligentRouter, RemediationTicket


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
