from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_parent_pin, require_parent_pin_dep
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """取得規則與獎項分類清單 (學業、常規、家事等)"""
    stmt = select(Category).order_by(Category.sort_order.asc(), Category.id.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=CategoryOut)
async def create_category(
    cat_in: CategoryCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """新增自訂規則分類（需家長安全鎖）"""
    pin = cat_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    existing = await db.execute(select(Category).where(Category.name == cat_in.name.strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分類名稱已存在")

    category = Category(
        name=cat_in.name.strip(),
        icon=cat_in.icon,
        sort_order=cat_in.sort_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category
