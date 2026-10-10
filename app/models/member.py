import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Member(Base):
    __tablename__ = "members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="child")  # 'parent' | 'child'
    avatar: Mapped[str] = mapped_column(String(255), default="🐸")
    current_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_earned_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pin_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 關聯
    rules: Mapped[List["RewardRule"]] = relationship("RewardRule", back_populates="member", cascade="all, delete-orphan")
    kudos_records: Mapped[List["KudosRecord"]] = relationship("KudosRecord", back_populates="member")
    redemptions: Mapped[List["Redemption"]] = relationship("Redemption", back_populates="member")
    badges: Mapped[List["MemberBadge"]] = relationship("MemberBadge", back_populates="member", cascade="all, delete-orphan")
