import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.member import Member
from app.models.reward_item import RewardItem
from app.models.redemption import Redemption
from app.schemas.redemption import RedemptionCreate, RedemptionReview, RedemptionOut
from app.core.security import verify_parent_pin
from app.services.line_service import send_line_push

async def create_redemption(
    db: AsyncSession,
    req: RedemptionCreate,
    background_tasks: BackgroundTasks,
) -> RedemptionOut:
    """
    發起獎品兌換申請 (FR-5, FR-15, FR-19)
    - 行級悲觀鎖 SELECT ... FOR UPDATE 防連點與超兌
    - 扣減即時可用點數 (狀態為 PENDING)
    - 背景非同步推播 LINE 兌換申請通知
    """
    # 1. 鎖定成員
    member_stmt = select(Member).where(Member.id == req.member_id).with_for_update()
    res_m = await db.execute(member_stmt)
    member = res_m.scalar_one_or_none()
    if not member or not member.is_active:
        raise HTTPException(status_code=400, detail="成員不存在或已被停用")

    # 2. 檢查兌換品項
    item = await db.get(RewardItem, req.item_id)
    if not item or not item.is_active:
        raise HTTPException(status_code=400, detail="獎勵品項不存在或已下架")

    # 3. 檢查點數是否充足
    if member.current_points < item.cost_points:
        diff = item.cost_points - member.current_points
        raise HTTPException(
            status_code=400,
            detail=f"點數不足！該品項需要 {item.cost_points} 點，目前僅有 {member.current_points} 點 (尚差 {diff} 點)",
        )

    # 4. 預扣點數並建立兌換紀錄 (PENDING)
    member.current_points -= item.cost_points

    redemption = Redemption(
        member_id=req.member_id,
        item_id=req.item_id,
        item_title_snapshot=item.title,
        points_spent=item.cost_points,
        status="PENDING",
        review_note=req.note,
    )
    db.add(redemption)
    await db.commit()
    await db.refresh(redemption)

    # 5. 排程非同步 LINE 推播通知 (FR-19)
    time_str = redemption.created_at.strftime("%Y-%m-%d %H:%M")
    push_msg = (
        f"🐸 [Frog Kudos 兌換申請通知]\n"
        f"成員: {member.name}\n"
        f"品項: {item.title}\n"
        f"扣除點數: {item.cost_points} 點\n"
        f"剩餘可用: {member.current_points} 點\n"
        f"時間: {time_str}\n"
        f"請家長至系統審核核銷。"
    )
    background_tasks.add_task(send_line_push, push_msg)

    return RedemptionOut.model_validate(redemption)

async def review_redemption(
    db: AsyncSession,
    redemption_id: uuid.UUID,
    req: RedemptionReview,
    parent_pin_header: Optional[str] = None,
) -> RedemptionOut:
    """
    家長審核兌換申請 (FR-15)
    - 驗證家長安全鎖 PIN 碼
    - 行級悲觀鎖保護
    - COMPLETE / APPROVE: 標記為 COMPLETED
    - REJECT: 標記為 REJECTED 並在同一交易中全額退還點數
    """
    pin = req.parent_pin or parent_pin_header
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    redemption_stmt = select(Redemption).where(Redemption.id == redemption_id).with_for_update()
    res = await db.execute(redemption_stmt)
    redemption = res.scalar_one_or_none()
    if not redemption:
        raise HTTPException(status_code=404, detail="查無此兌換紀錄")

    if redemption.status != "PENDING":
        raise HTTPException(status_code=400, detail="此申請已審核完成，不可重複操作")

    action = req.action.upper()
    now = datetime.now(timezone.utc)

    if action in ("COMPLETE", "APPROVE"):
        redemption.status = "COMPLETED"
        redemption.reviewed_at = now
        if req.review_note:
            redemption.review_note = req.review_note
    elif action == "REJECT":
        redemption.status = "REJECTED"
        redemption.reviewed_at = now
        redemption.review_note = req.review_note or "家長退回申請"

        # 全額退還點數
        member_stmt = select(Member).where(Member.id == redemption.member_id).with_for_update()
        res_m = await db.execute(member_stmt)
        member = res_m.scalar_one_or_none()
        if member:
            member.current_points += redemption.points_spent
    else:
        raise HTTPException(status_code=400, detail=f"不支援的審核動作: {req.action}")

    await db.commit()
    await db.refresh(redemption)
    return RedemptionOut.model_validate(redemption)

async def list_redemptions(
    db: AsyncSession,
    member_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
) -> List[RedemptionOut]:
    """查詢兌換歷史紀錄清單"""
    stmt = select(Redemption)
    if member_id:
        stmt = stmt.where(Redemption.member_id == member_id)
    if status:
        stmt = stmt.where(Redemption.status == status.upper())

    stmt = stmt.order_by(Redemption.created_at.desc())
    res = await db.execute(stmt)
    return [RedemptionOut.model_validate(r) for r in res.scalars().all()]
