"""
Provenance Header:
  Task-ID: TASK-001
  ADR-Ref: ADR-001
  Author: BackendEngineerAgent
  Contract: api-spec.yaml
"""

import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IntegrationPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)


class IntegrationResponse(BaseModel):
    id: str
    name: str
    status: str = "ACTIVE"


class IntegrationService:
    def __init__(self):
        self._db: Dict[str, Dict[str, Any]] = {}

    def create_integration(self, payload: IntegrationPayload) -> IntegrationResponse:
        entity_id = str(uuid.uuid4())
        record = {
            "id": entity_id,
            "name": payload.name,
            "category": payload.category,
            "status": "ACTIVE"
        }
        self._db[entity_id] = record
        return IntegrationResponse(id=entity_id, name=payload.name, status="ACTIVE")

    def get_integration(self, entity_id: str) -> Optional[IntegrationResponse]:
        record = self._db.get(entity_id)
        if not record:
            return None
        return IntegrationResponse(id=record["id"], name=record["name"], status=record["status"])
