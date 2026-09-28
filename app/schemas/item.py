import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RewardItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    cost_points: int = Field(..., gt=0)
    icon: str = Field(default="🎁", max_length=50)
    parent_pin: Optional[str] = None

class RewardItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    cost_points: Optional[int] = Field(default=None, gt=0)
    icon: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None
    parent_pin: Optional[str] = None

class RewardItemOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    cost_points: int
    icon: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
