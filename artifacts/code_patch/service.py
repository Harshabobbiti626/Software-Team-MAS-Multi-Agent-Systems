"""
Provenance Header:
  Task-ID: TASK-1793341811701
  ADR-Ref: ADR-001
  Author: BackendEngineerAgent
  Contract: api-spec.yaml
"""

import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ResourcePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)


class ResourceResponse(BaseModel):
    id: str
    name: str
    status: str = "ACTIVE"


class ResourceService:
    def __init__(self):
        self._db: Dict[str, Dict[str, Any]] = {}

    def create_resource(self, payload: ResourcePayload) -> ResourceResponse:
        entity_id = str(uuid.uuid4())
        record = {
            "id": entity_id,
            "name": payload.name,
            "category": payload.category,
            "status": "ACTIVE"
        }
        self._db[entity_id] = record
        return ResourceResponse(id=entity_id, name=payload.name, status="ACTIVE")

    def get_resource(self, entity_id: str) -> Optional[ResourceResponse]:
        record = self._db.get(entity_id)
        if not record:
            return None
        return ResourceResponse(id=record["id"], name=record["name"], status=record["status"])
