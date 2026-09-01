from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ConstructPartCreate(BaseModel):
    part_id: UUID
    position_order: int
    orientation: str = "forward"


class ConstructCreate(BaseModel):
    name: str
    full_sequence: str
    parts: Optional[list[ConstructPartCreate]] = None
    metadata: Optional[dict] = None


class ConstructResponse(BaseModel):
    id: UUID
    name: str
    full_sequence: str
    version: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
