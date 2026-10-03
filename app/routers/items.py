import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_parent_pin, require_parent_pin_dep
from app.models.reward_item import RewardItem
from app.schemas.item import RewardItemCreate, RewardItemUpdate, RewardItemOut

router = APIRouter(prefix="/items", tags=["Reward Items"])

@router.get("", response_model=List[RewardItemOut])
async def list_items(
    include_inactive: bool = Query(False, alias="all", description="是否列出所有品項 (含已下架)"),
    db: AsyncSession = Depends(get_db),
):
    """查詢兌換商城品項清單（預設僅列出上架中品項）"""
    stmt = select(RewardItem)
    if not include_inactive:
        stmt = stmt.where(RewardItem.is_active == True)
    stmt = stmt.order_by(RewardItem.cost_points.asc(), RewardItem.created_at.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=RewardItemOut)
async def create_item(
    item_in: RewardItemCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """新增商城獎品（需家長安全鎖）"""
    pin = item_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    item = RewardItem(
        title=item_in.title.strip(),
        description=item_in.description,
        cost_points=item_in.cost_points,
        icon=item_in.icon,
        is_active=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/{item_id}", response_model=RewardItemOut)
async def update_item(
    item_id: uuid.UUID,
    item_in: RewardItemUpdate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """編輯商城獎品內容或上下架狀態（需家長安全鎖）"""
    pin = item_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    item = await db.get(RewardItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="獎品不存在")

    if item_in.title is not None:
        item.title = item_in.title.strip()
    if item_in.description is not None:
        item.description = item_in.description
    if item_in.cost_points is not None:
        item.cost_points = item_in.cost_points
    if item_in.icon is not None:
        item.icon = item_in.icon
    if item_in.is_active is not None:
        item.is_active = item_in.is_active

    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{item_id}")
async def delete_item(
    item_id: uuid.UUID,
    permanent: bool = Query(False, description="是否永久實體刪除 (僅在無兌換紀錄時允許)"),
    parent_pin: Optional[str] = None,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """下架軟刪除商城獎品 (is_active = FALSE，需家長安全鎖)；若 permanent=True 且無兌換關聯則實體刪除"""
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    item = await db.get(RewardItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="獎品不存在")

    if permanent:
        from app.models.redemption import Redemption
        chk = await db.execute(select(Redemption).where(Redemption.item_id == item_id))
        if chk.scalars().first():
            item.is_active = False
            await db.commit()
            return {"success": True, "message": "獎品已有歷史兌換紀錄，已安全保留並設定為下架狀態"}
        await db.delete(item)
        await db.commit()
        return {"success": True, "message": "獎品已永久刪除"}

    item.is_active = False
    await db.commit()
    return {"success": True, "message": "獎品已下架"}

