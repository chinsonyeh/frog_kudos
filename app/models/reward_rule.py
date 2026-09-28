import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class RewardRule(Base):
    __tablename__ = "reward_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
    )
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False, default="NUM_GTE")  # 'NUM_GTE', 'NUM_EQ', 'EXACT'
    condition_value: Mapped[str] = mapped_column(String(50), nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 關聯
    member: Mapped[Optional["Member"]] = relationship("Member", back_populates="rules")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="rules")
    kudos_records: Mapped[List["KudosRecord"]] = relationship("KudosRecord", back_populates="rule")
