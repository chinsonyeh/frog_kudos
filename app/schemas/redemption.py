import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RedemptionCreate(BaseModel):
    member_id: uuid.UUID
    item_id: uuid.UUID
    note: Optional[str] = None
    pin: Optional[str] = None
    parent_pin: Optional[str] = None

class RedemptionReview(BaseModel):
    action: str = Field(..., pattern="^(COMPLETE|REJECT|APPROVE)$")  # 支援 APPROVE 作為 COMPLETE 別名
    review_note: Optional[str] = None
    parent_pin: Optional[str] = None

class RedemptionOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    item_id: Optional[uuid.UUID] = None
    item_title_snapshot: str
    points_spent: int
    status: str  # 'PENDING', 'COMPLETED', 'REJECTED'
    review_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
