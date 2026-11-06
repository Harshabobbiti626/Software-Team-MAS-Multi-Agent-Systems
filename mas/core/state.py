"""
Immutable State Schemas & Typed Artifacts for MAS.
Every entity, artifact, and transition is governed by strict Pydantic schemas.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    CONSULTING_RFC = "CONSULTING_RFC"
    REVIEW_PENDING = "REVIEW_PENDING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SubsystemClass(str, Enum):
    BUSINESS = "BUSINESS"
    ARCHITECTURE = "ARCHITECTURE"
    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"
    DATA = "DATA"
    CLOUD_DEVOPS = "CLOUD_DEVOPS"
    SECURITY = "SECURITY"
    QUALITY = "QUALITY"
    DOCUMENTATION = "DOCUMENTATION"
    FULL_SYSTEM = "FULL_SYSTEM"


class ArtifactType(str, Enum):
    PRD = "PRD"
    ADR = "ADR"
    API_SPEC = "API_SPEC"
    SCHEMA_SQL = "SCHEMA_SQL"
    CODE_PATCH = "CODE_PATCH"
    TEST_REPORT = "TEST_REPORT"
    CDR = "CDR"  # Consensus Decision Record
    AUDIT_DOSSIER = "AUDIT_DOSSIER"
    DOCUMENTATION = "DOCUMENTATION"
    SECURITY_AUDIT = "SECURITY_AUDIT"
    DOMAIN_VALIDATION = "DOMAIN_VALIDATION"


class UserStory(BaseModel):
    id: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: List[str] = Field(default_factory=list)


class PRD(BaseModel):
    id: str
    title: str
    business_goal_id: str
    executive_summary: str
    user_stories: List[UserStory] = Field(default_factory=list)
    non_functional_requirements: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ADRStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ADR(BaseModel):
    id: str
    title: str
    status: ADRStatus = ADRStatus.ACCEPTED
    context: str
    decision: str
    consequences: List[str] = Field(default_factory=list)
    trade_offs: Dict[str, str] = Field(default_factory=dict)
    reversibility: str = "two-way"  # "one-way" vs "two-way"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CodePatch(BaseModel):
    id: str
    task_id: str
    author_role: str
    file_path: str
    diff: str
    commit_hash: Optional[str] = None
    description: str = ""
    provenance_header: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TestReport(BaseModel):
    __test__ = False
    id: str
    task_id: str
    test_suite: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    failure_signatures: List[str] = Field(default_factory=list)
    passed_all: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusDecisionRecord(BaseModel):
    id: str
    rfc_id: str
    topic: str
    participants: List[str] = Field(default_factory=list)
    agreed_resolution: str
    contract_updates: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Artifact(BaseModel):
    id: str
    type: ArtifactType
    name: str
    path: str
    content: str
    version: int = 1
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version_history: List[Dict[str, Any]] = Field(default_factory=list)


class Task(BaseModel):
    id: str
    title: str
    description: str
    business_goal_id: str = "GOAL-001"
    assigned_pod: SubsystemClass = SubsystemClass.FULL_SYSTEM
    priority: TaskPriority = TaskPriority.HIGH
    status: TaskStatus = TaskStatus.PENDING
    subtasks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenUsageTracker(BaseModel):
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0

    def add(self, prompt: int = 0, candidate: int = 0, thinking: int = 0) -> None:
        self.prompt_tokens += prompt
        self.candidate_tokens += candidate
        self.thinking_tokens += thinking
        self.total_tokens = self.prompt_tokens + self.candidate_tokens + self.thinking_tokens


class SystemState(BaseModel):
    session_id: str
    current_task: Optional[Task] = None
    artifacts: Dict[str, Artifact] = Field(default_factory=dict)
    active_pods: List[str] = Field(default_factory=list)
    turn_count: int = 0
    consecutive_failures: int = 0
    usage: TokenUsageTracker = Field(default_factory=TokenUsageTracker)
    is_terminated: bool = False
    circuit_broken: bool = False
    termination_reason: Optional[str] = None
    history_events: List[Dict[str, Any]] = Field(default_factory=list)
