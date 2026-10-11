import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class BadgeBase(BaseModel):
    title: str = Field(..., max_length=100)
    description: str = Field(..., max_length=255)
    icon: str = Field("🏅", max_length=20)
    condition_type: str = Field("TOTAL_POINTS", description="TOTAL_POINTS, PERFECT_SCORE_COUNT, CHORE_POINTS, CUSTOM")
    target_value: int = Field(100, ge=1)
    reward_points: Optional[int] = Field(None, ge=0, description="達成解鎖時額外發放的獎勵點數 (未指定時預設門檻的 25%)")
    is_repeatable: bool = Field(True, description="達成解鎖並獲取點數後，是否自動重設並可循環累積再次達成")
    sort_order: int = Field(0)
    is_active: bool = True

class BadgeCreate(BadgeBase):
    badge_key: Optional[str] = None
    parent_pin: Optional[str] = None

class BadgeUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    icon: Optional[str] = Field(None, max_length=20)
    condition_type: Optional[str] = None
    target_value: Optional[int] = Field(None, ge=1)
    reward_points: Optional[int] = Field(None, ge=0)
    is_repeatable: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    parent_pin: Optional[str] = None

class BadgeOut(BadgeBase):
    id: uuid.UUID
    badge_key: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class MemberBadgeOut(BaseModel):
    id: Optional[uuid.UUID] = None
    badge_key: str
    title: str
    description: str
    icon: str
    condition_type: str = "TOTAL_POINTS"
    reward_points: int = 0
    is_repeatable: bool = True
    unlocked: bool
    unlocked_count: int = 0
    unlocked_at: Optional[datetime] = None
    last_unlocked_at: Optional[datetime] = None
    progress: int = 0
    target: int = 0

    model_config = {"from_attributes": True}
