from typing import List
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="📚")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 關聯
    rules: Mapped[List["RewardRule"]] = relationship("RewardRule", back_populates="category")
