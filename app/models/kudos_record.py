import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class KudosRecord(Base):
    __tablename__ = "kudos_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="RESTRICT"),
        nullable=False
    )
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reward_rules.id", ondelete="SET NULL"),
        nullable=True
    )
    target_name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    condition_snapshot: Mapped[str] = mapped_column(String(100), nullable=False, default="自訂")
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_detail_snapshot: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adjustment_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(50), nullable=False, default="Parent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 關聯
    member: Mapped["Member"] = relationship("Member", back_populates="kudos_records")
    rule: Mapped[Optional["RewardRule"]] = relationship("RewardRule", back_populates="kudos_records")
