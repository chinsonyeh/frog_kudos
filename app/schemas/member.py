import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class MemberCreate(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(default="child", pattern="^(parent|child)$")
    avatar: str = Field(default="🐸", max_length=255)
    pin_code: Optional[str] = Field(default=None, description="成員 4 碼 PIN 碼 (預設 0000)")
    parent_pin: Optional[str] = None

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    role: Optional[str] = Field(default=None, pattern="^(parent|child)$")
    avatar: Optional[str] = Field(default=None, max_length=255)
    pin_code: Optional[str] = None
    is_active: Optional[bool] = None
    parent_pin: Optional[str] = None

class MemberAvatarUpdate(BaseModel):
    avatar: str = Field(..., min_length=1, max_length=255)

class MemberChangePinIn(BaseModel):
    old_pin: Optional[str] = None
    new_pin: str = Field(..., min_length=4, max_length=6)
    parent_pin: Optional[str] = None

class MemberOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    avatar: str
    current_points: int
    total_earned_points: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # 注意：pin_code 絕不包含在此 Response Schema 中 (NFR-4)
    model_config = {"from_attributes": True}

class ParentPinVerify(BaseModel):
    pin: str
