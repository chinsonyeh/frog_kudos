from typing import Optional
from pydantic import BaseModel, Field

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    icon: str = Field(default="📚", max_length=50)
    sort_order: int = Field(default=0)
    parent_pin: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str
    sort_order: int

    model_config = {"from_attributes": True}
