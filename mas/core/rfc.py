"""
Cross-Pod Request for Consultation (RFC) Protocol.
Enables structured peer consultation, trade-off negotiation, and formal Consensus Decision Records (CDR)
without chaotic chat swarms.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from mas.core.blackboard import ArtifactBlackboard
from mas.core.state import ArtifactType, ConsensusDecisionRecord


class RFCRequest(BaseModel):
    rfc_id: str
    requester_role: str
    target_role: str
    topic: str
    problem_statement: str
    proposed_alternatives: List[str] = Field(default_factory=list)
    trade_offs: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RFCResponse(BaseModel):
    rfc_id: str
    responder_role: str
    analysis: str
    counter_proposal: Optional[str] = None
    recommendation: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RFCManager:
    def __init__(self, blackboard: Optional[ArtifactBlackboard] = None):
        self.blackboard = blackboard
        self._rfcs: Dict[str, RFCRequest] = {}
        self._responses: Dict[str, List[RFCResponse]] = {}
        self._cdrs: Dict[str, ConsensusDecisionRecord] = {}

    def submit_request(
        self,
        rfc_id: str,
        requester_role: str,
        target_role: str,
        topic: str,
        problem_statement: str,
        proposed_alternatives: List[str],
        trade_offs: Dict[str, str],
    ) -> RFCRequest:
        request = RFCRequest(
            rfc_id=rfc_id,
            requester_role=requester_role,
            target_role=target_role,
            topic=topic,
            problem_statement=problem_statement,
            proposed_alternatives=proposed_alternatives,
            trade_offs=trade_offs,
        )
        self._rfcs[rfc_id] = request
        self._responses[rfc_id] = []
        return request

    def submit_response(
        self,
        rfc_id: str,
        responder_role: str,
        analysis: str,
        recommendation: str,
        counter_proposal: Optional[str] = None,
    ) -> RFCResponse:
        if rfc_id not in self._rfcs:
            raise KeyError(f"RFC {rfc_id} not found")

        resp = RFCResponse(
            rfc_id=rfc_id,
            responder_role=responder_role,
            analysis=analysis,
            recommendation=recommendation,
            counter_proposal=counter_proposal,
        )
        self._responses[rfc_id].append(resp)
        return resp

    def reach_consensus(
        self,
        cdr_id: str,
        rfc_id: str,
        agreed_resolution: str,
        contract_updates: Optional[Dict[str, str]] = None,
    ) -> ConsensusDecisionRecord:
        if rfc_id not in self._rfcs:
            raise KeyError(f"RFC {rfc_id} not found")

        rfc = self._rfcs[rfc_id]
        participants = [rfc.requester_role, rfc.target_role]
        for r in self._responses.get(rfc_id, []):
            if r.responder_role not in participants:
                participants.append(r.responder_role)

        cdr = ConsensusDecisionRecord(
            id=cdr_id,
            rfc_id=rfc_id,
            topic=rfc.topic,
            participants=participants,
            agreed_resolution=agreed_resolution,
            contract_updates=contract_updates or {},
        )
        self._cdrs[cdr_id] = cdr

        # Register to blackboard if available
        if self.blackboard:
            cdr_markdown = f"""# Consensus Decision Record ({cdr.id})
**Topic**: {cdr.topic}  
**RFC ID**: {cdr.rfc_id}  
**Participants**: {", ".join(cdr.participants)}  
**Agreed Resolution**:  
{cdr.agreed_resolution}

## Contract Updates:
{chr(10).join(f"- `{k}`: {v}" for k, v in cdr.contract_updates.items()) if cdr.contract_updates else "None"}
"""
            self.blackboard.register_artifact(
                artifact_id=cdr.id,
                artifact_type=ArtifactType.CDR,
                name=f"{cdr.id}.md",
                content=cdr_markdown,
                created_by="RFCManager",
            )

        return cdr

    def get_rfc(self, rfc_id: str) -> Optional[RFCRequest]:
        return self._rfcs.get(rfc_id)

    def get_responses(self, rfc_id: str) -> List[RFCResponse]:
        return self._responses.get(rfc_id, [])

    def get_cdr(self, cdr_id: str) -> Optional[ConsensusDecisionRecord]:
        return self._cdrs.get(cdr_id)
