import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RuleCreate(BaseModel):
    member_id: Optional[uuid.UUID] = Field(default=None, description="若為 NULL 代表全家通用規則")
    category_id: Optional[int] = None
    target_name: str = Field(..., min_length=1, max_length=100)
    match_type: str = Field(default="NUM_GTE", pattern="^(NUM_GTE|NUM_EQ|EXACT)$")
    condition_value: str = Field(..., min_length=1, max_length=50)
    reward_points: int = Field(..., ge=0)
    description: Optional[str] = None
    parent_pin: Optional[str] = None

class RuleUpdate(BaseModel):
    member_id: Optional[uuid.UUID] = None
    category_id: Optional[int] = None
    target_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    match_type: Optional[str] = Field(default=None, pattern="^(NUM_GTE|NUM_EQ|EXACT)$")
    condition_value: Optional[str] = Field(default=None, min_length=1, max_length=50)
    reward_points: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    parent_pin: Optional[str] = None

class RuleOut(BaseModel):
    id: uuid.UUID
    member_id: Optional[uuid.UUID] = None
    category_id: Optional[int] = None
    target_name: str
    match_type: str
    condition_value: str
    reward_points: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
