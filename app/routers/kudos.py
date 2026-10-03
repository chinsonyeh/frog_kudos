import uuid
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_parent_pin_dep, require_any_pin_dep
from app.schemas.kudos import (
    PreviewIn,
    PreviewOut,
    KudosRecordCreate,
    KudosRecordOut,
    LedgerItemOut,
    BatchPreviewIn,
    BatchPreviewOut,
    BatchAdjustIn,
    BatchAdjustOut,
)
from app.services.rule_engine import match_rule
from app.services.kudos_service import (
    record_kudos,
    get_ledger_history,
    export_ledger_csv,
    preview_batch_adjustment,
    execute_batch_adjustment,
)

router = APIRouter(prefix="/kudos", tags=["Kudos & Ledger"])

@router.post("/preview", response_model=PreviewOut)
async def preview_kudos_rule(
    preview_in: PreviewIn,
    db: AsyncSession = Depends(get_db),
):
    """智慧即時試算預覽（支援輸入文字防呆降級，FR-3）"""
    return await match_rule(
        db=db,
        member_id=preview_in.member_id,
        target_name=preview_in.target_name,
        condition_value=preview_in.condition_value,
    )

@router.post("/record", response_model=KudosRecordOut)
async def create_kudos_record(
    record_in: KudosRecordCreate,
    x_pin: Optional[str] = Depends(require_any_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """正式發放點數或自訂臨時獎懲 (FR-3, FR-4, FR-14)"""
    return await record_kudos(
        db=db,
        record_in=record_in,
        parent_pin_header=x_pin,
    )

@router.get("/history", response_model=List[LedgerItemOut])
async def list_ledger_history(
    member_id: Optional[uuid.UUID] = Query(None, description="過濾特定成員存摺流水帳"),
    limit: int = Query(50, ge=1, le=500, description="回傳筆數上限"),
    db: AsyncSession = Depends(get_db),
):
    """查詢家庭綜合存摺流水帳 (FR-6)"""
    return await get_ledger_history(db=db, member_id=member_id, limit=limit)

@router.get("/export")
async def export_ledger(
    member_id: Optional[uuid.UUID] = Query(None, description="過濾特定成員"),
    start_date: Optional[date] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="截止日期 (YYYY-MM-DD，全日包含)"),
    db: AsyncSession = Depends(get_db),
):
    """匯出學期成就獲得與兌換支出之綜合存摺 CSV 檔案 (FR-17)"""
    csv_content = await export_ledger_csv(
        db=db,
        member_id=member_id,
        start_date=start_date,
        end_date=end_date,
    )
    filename = f"kudos_ledger_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.post("/batch-preview", response_model=BatchPreviewOut)
async def preview_batch_adjust(
    preview_in: BatchPreviewIn,
    db: AsyncSession = Depends(get_db),
):
    """歷史積分批次調整預覽試算 (FR-7)"""
    return await preview_batch_adjustment(db=db, preview_in=preview_in)

@router.post("/batch-adjust", response_model=BatchAdjustOut)
async def execute_batch_adjust(
    adjust_in: BatchAdjustIn,
    x_parent_pin: Optional[str] = Depends(require_parent_pin_dep),
    db: AsyncSession = Depends(get_db),
):
    """執行歷史積分批次統一調整 (FR-7)"""
    return await execute_batch_adjustment(
        db=db,
        adjust_in=adjust_in,
        parent_pin_header=x_parent_pin,
    )
