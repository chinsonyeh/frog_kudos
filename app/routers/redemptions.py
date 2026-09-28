import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_parent_pin_dep
from app.schemas.redemption import RedemptionCreate, RedemptionReview, RedemptionOut
from app.services.redemption_service import (
    create_redemption,
    review_redemption,
    list_redemptions,
)

router = APIRouter(prefix="/redemptions", tags=["Redemptions"])

@router.post("", response_model=RedemptionOut)
async def request_redemption(
    redemption_in: RedemptionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    發起獎勵兌換申請 (FR-5)
    - 行級悲觀鎖防併發
    - 扣除即時可用點數並建立 PENDING 申請
    - 背景非同步發送 LINE 提醒家長 (FR-19)
    """
    return await create_redemption(
        db=db,
        req=redemption_in,
        background_tasks=background_tasks,
    )

@router.get("", response_model=List[RedemptionOut])
async def get_redemptions(
    member_id: Optional[uuid.UUID] = Query(None, description="過濾特定成員"),
    status: Optional[str] = Query(None, description="過濾狀態 (PENDING, COMPLETED, REJECTED)"),
    db: AsyncSession = Depends(get_db),
):
    """查詢兌換與核銷歷史紀錄 (FR-5, FR-15)"""
    return await list_redemptions(db=db, member_id=member_id, status=status)

@router.post("/{redemption_id}/review", response_model=RedemptionOut)
async def review_redemption_endpoint(
    redemption_id: uuid.UUID,
    review_in: RedemptionReview,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """
    家長審核核銷或退回退點 (FR-15)
    - COMPLETE / APPROVE: 標記為核銷完成
    - REJECT: 標記為退回並全額退還點數
    """
    return await review_redemption(
        db=db,
        redemption_id=redemption_id,
        req=review_in,
        parent_pin_header=x_parent_pin,
    )
