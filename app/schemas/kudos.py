import uuid
from datetime import datetime, date
from typing import Optional, Any, List
from pydantic import BaseModel, Field
from app.schemas.badge import MemberBadgeOut

# 智慧試算預覽
class PreviewIn(BaseModel):
    member_id: uuid.UUID
    target_name: str
    condition_value: Optional[str] = None

class PreviewOut(BaseModel):
    matched: bool
    suggested_points: int
    rule_id: Optional[uuid.UUID] = None
    rule_name: Optional[str] = None

# 正式登記紀錄
class KudosRecordCreate(BaseModel):
    member_id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None
    target_name: str = Field(..., min_length=1, max_length=100)
    condition_value: Optional[str] = Field(default="自訂", max_length=100)
    points_awarded: int
    note: Optional[str] = None
    recorded_by: str = Field(default="Parent", max_length=50)
    parent_pin: Optional[str] = None
    pin: Optional[str] = None

class KudosRecordOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None
    target_name_snapshot: str
    condition_snapshot: str
    points_awarded: int
    rule_detail_snapshot: Optional[Any] = None
    note: Optional[str] = None
    adjustment_note: Optional[str] = None
    recorded_by: str
    created_at: datetime
    updated_at: datetime
    newly_unlocked_badges: List[MemberBadgeOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

# 綜合存摺流水帳
class LedgerItemOut(BaseModel):
    id: uuid.UUID
    record_type: str  # 'KUDOS' | 'REDEMPTION'
    title: str
    points: int
    condition_or_status: str
    note: Optional[str] = None
    actor: str
    created_at: datetime

# 批次調整預覽
class BatchPreviewIn(BaseModel):
    member_id: uuid.UUID
    target_name: str
    start_date: date
    end_date: date
    mode: str = Field(..., pattern="^(FIXED|OFFSET)$")
    value: int

class BatchPreviewItem(BaseModel):
    id: uuid.UUID
    target_name: str
    condition: str
    old_points: int
    new_points: int
    delta: int
    created_at: datetime

class BatchPreviewOut(BaseModel):
    affected_count: int
    original_total: int
    new_total: int
    delta: int
    items: List[BatchPreviewItem]

# 批次調整執行
class BatchAdjustIn(BaseModel):
    member_id: uuid.UUID
    target_name: str
    start_date: date
    end_date: date
    mode: str = Field(..., pattern="^(FIXED|OFFSET)$")
    value: int
    reason: str = Field(..., min_length=1)
    parent_pin: Optional[str] = None

class BatchAdjustOut(BaseModel):
    affected_count: int
    total_points_delta: int
    member_current_points: int
    member_total_earned_points: int
    newly_unlocked_badges: List[MemberBadgeOut] = Field(default_factory=list)
