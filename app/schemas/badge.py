from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class MemberBadgeOut(BaseModel):
    badge_key: str
    title: str
    description: str
    icon: str
    unlocked: bool
    unlocked_at: Optional[datetime] = None
    progress: int = 0
    target: int = 0

    model_config = {"from_attributes": True}
