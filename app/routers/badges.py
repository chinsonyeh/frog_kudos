import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_parent_pin, require_parent_pin_dep
from app.schemas.badge import BadgeCreate, BadgeUpdate, BadgeOut
from app.services.badge_service import (
    get_all_badges,
    create_badge,
    update_badge,
    delete_badge,
    toggle_member_badge,
)

router = APIRouter(prefix="/badges", tags=["Badges"])

@router.get("", response_model=List[BadgeOut])
async def list_badges(
    include_inactive: bool = Query(False, alias="all", description="是否包含已停用之勳章定義"),
    db: AsyncSession = Depends(get_db),
):
    """查詢所有里程碑成就勳章定義清單 (FR-18)"""
    return await get_all_badges(db, active_only=not include_inactive)

@router.post("", response_model=BadgeOut)
async def add_badge(
    badge_in: BadgeCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """新增自訂成就勳章或里程碑 (需家長 PIN 碼)"""
    pin = badge_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    return await create_badge(db, badge_in)

@router.put("/{badge_id}", response_model=BadgeOut)
async def modify_badge(
    badge_id: uuid.UUID,
    badge_in: BadgeUpdate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """編輯成就勳章資訊、條件門檻或啟用狀態 (需家長 PIN 碼)"""
    pin = badge_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    return await update_badge(db, badge_id, badge_in)

@router.delete("/{badge_id}")
async def remove_badge(
    badge_id: uuid.UUID,
    parent_pin: Optional[str] = Query(None),
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """刪除或停用成就勳章 (若已有成員解鎖則安全停用，需家長 PIN 碼)"""
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    return await delete_badge(db, badge_id)

@router.post("/{badge_key}/toggle/{member_id}")
async def toggle_badge_for_member(
    badge_key: str,
    member_id: uuid.UUID,
    unlock: Optional[bool] = Body(None, embed=True),
    parent_pin: Optional[str] = Body(None, embed=True),
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """手動為特定成員頒發或收回榮譽勳章 (需家長 PIN 碼)"""
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    return await toggle_member_badge(db, badge_key, member_id, unlock)
