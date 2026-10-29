"""
Human-in-the-Loop (HITL) Governance & Gating Matrix for MAS.
"""

from mas.hitl.gates import HITLGateManager, GateDecision, GateLevel
from mas.hitl.policies import EscalationPolicy

__all__ = ["HITLGateManager", "GateDecision", "GateLevel", "EscalationPolicy"]
