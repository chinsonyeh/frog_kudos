import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.database import get_db
from app.core.security import verify_parent_pin, hash_pin, require_parent_pin_dep
from app.models.member import Member
from app.models.kudos_record import KudosRecord
from app.models.redemption import Redemption
from app.schemas.member import MemberCreate, MemberUpdate, MemberAvatarUpdate, MemberOut
from app.schemas.badge import MemberBadgeOut
from app.services.badge_service import get_member_badges

router = APIRouter(prefix="/members", tags=["Members"])

@router.get("", response_model=List[MemberOut])
async def list_members(
    include_inactive: bool = Query(False, description="是否包含已停用成員"),
    db: AsyncSession = Depends(get_db),
):
    """取得家庭成員清單（預設僅列出有效成員）"""
    stmt = select(Member)
    if not include_inactive:
        stmt = stmt.where(Member.is_active == True)
    stmt = stmt.order_by(Member.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("", response_model=MemberOut)
async def create_member(
    member_in: MemberCreate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """新增家庭成員（需家長安全鎖）"""
    pin = member_in.parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    # 檢查姓名是否已存在
    existing = await db.execute(select(Member).where(Member.name == member_in.name.strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="成員姓名已存在")

    hashed_pin = None
    if member_in.role == "parent":
        if not member_in.pin_code:
            raise HTTPException(status_code=400, detail="新增家長成員時必須設定 4 碼 PIN 碼")
        hashed_pin = hash_pin(member_in.pin_code)

    new_member = Member(
        name=member_in.name.strip(),
        role=member_in.role,
        avatar=member_in.avatar,
        pin_code=hashed_pin,
        current_points=0,
        total_earned_points=0,
        is_active=True,
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)
    return new_member

@router.put("/{member_id}", response_model=MemberOut)
async def update_member(
    member_id: uuid.UUID,
    member_in: MemberUpdate,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    修改家庭成員資訊、變更家長 PIN 碼或停用狀態。
    若僅變更頭像 (avatar)，未解鎖狀態下亦允許變更（無須家長安全鎖）；
    若涉及姓名、角色、PIN 碼、啟用狀態等管理屬性，必須通過家長安全鎖驗證。
    """
    # 檢查是否僅變更頭像 (未解鎖時仍可更換頭像)
    is_avatar_only = (
        member_in.avatar is not None
        and member_in.name is None
        and member_in.role is None
        and member_in.pin_code is None
        and member_in.is_active is None
    )

    if not is_avatar_only:
        pin = member_in.parent_pin or x_parent_pin
        if not await verify_parent_pin(db, pin):
            raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")

    if member_in.name is not None and member_in.name.strip() != member.name:
        existing = await db.execute(select(Member).where(Member.name == member_in.name.strip()))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="成員姓名已被使用")
        member.name = member_in.name.strip()

    if member_in.role is not None:
        member.role = member_in.role
    if member_in.avatar is not None:
        member.avatar = member_in.avatar
    if member_in.pin_code is not None:
        member.pin_code = hash_pin(member_in.pin_code) if member_in.pin_code.strip() else None
    if member_in.is_active is not None:
        member.is_active = member_in.is_active

    await db.commit()
    await db.refresh(member)
    return member

@router.patch("/{member_id}/avatar", response_model=MemberOut)
async def update_member_avatar(
    member_id: uuid.UUID,
    avatar_in: MemberAvatarUpdate,
    db: AsyncSession = Depends(get_db),
):
    """允許小孩或未解鎖模式下自由更換個人代表頭像 (無須家長安全鎖)"""
    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")
    member.avatar = avatar_in.avatar
    await db.commit()
    await db.refresh(member)
    return member

@router.delete("/{member_id}")
async def delete_or_deactivate_member(
    member_id: uuid.UUID,
    parent_pin: Optional[str] = None,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    安全刪除或停用成員 (FR-1)
    若已有歷史紀錄則轉為軟停用 (is_active=False) 以保全審計鏈；若為全新無紀錄成員則實體刪除。
    """
    pin = parent_pin or x_parent_pin
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")

    # 檢查是否有歷史紀錄
    kudos_count_res = await db.execute(
        select(func.count(KudosRecord.id)).where(KudosRecord.member_id == member_id)
    )
    kudos_count = kudos_count_res.scalar() or 0

    red_count_res = await db.execute(
        select(func.count(Redemption.id)).where(Redemption.member_id == member_id)
    )
    red_count = red_count_res.scalar() or 0

    if kudos_count > 0 or red_count > 0:
        member.is_active = False
        await db.commit()
        return {"success": True, "action": "DEACTIVATED", "message": "成員已有歷史紀錄，已自動轉為停用狀態"}
    else:
        await db.delete(member)
        await db.commit()
        return {"success": True, "action": "DELETED", "message": "全新成員無歷史紀錄，已徹底刪除"}

@router.get("/{member_id}/badges", response_model=List[MemberBadgeOut])
async def list_member_badges(
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """查詢成員里程碑成就勳章清單與達成進度 (FR-18)"""
    return await get_member_badges(db, member_id)
