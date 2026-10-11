import uuid
import csv
import io
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, List
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.member import Member
from app.models.reward_rule import RewardRule
from app.models.kudos_record import KudosRecord
from app.models.redemption import Redemption
from app.schemas.kudos import (
    KudosRecordCreate,
    KudosRecordOut,
    KudosReviewIn,
    LedgerItemOut,
    BatchPreviewIn,
    BatchPreviewItem,
    BatchPreviewOut,
    BatchAdjustIn,
    BatchAdjustOut,
)
from app.core.security import verify_parent_pin, verify_member_or_parent_pin
from app.services.badge_service import evaluate_and_unlock_badges
from app.services.line_service import send_line_push

async def record_kudos(
    db: AsyncSession,
    record_in: KudosRecordCreate,
    background_tasks: Optional[BackgroundTasks] = None,
    parent_pin_header: Optional[str] = None,
) -> KudosRecordOut:
    """
    正式發放點數或小孩發起加點申請 (FR-3, FR-4, FR-14)
    - 驗證 PIN 碼與操作人身分 (小孩僅能登記自身且點數 > 0)
    - 小孩登記：狀態為 PENDING，暫不加點數與解鎖勳章，排程發送 LINE 通知家長
    - 家長登記：狀態為 APPROVED，即時增減雙軌點數並評估里程碑勳章
    - 封存規則細節快照與歷史紀錄
    """
    if record_in.parent_pin or parent_pin_header:
        parent_pin_val = record_in.parent_pin or parent_pin_header
        valid, auth_role = await verify_member_or_parent_pin(db, record_in.member_id, header_pin=parent_pin_val)
    else:
        valid, auth_role = await verify_member_or_parent_pin(db, record_in.member_id, input_pin=record_in.pin)
    if not valid:
        raise HTTPException(status_code=403, detail="PIN 碼錯誤或未授權")

    # 1. 悲觀鎖查詢成員
    member_stmt = select(Member).where(Member.id == record_in.member_id).with_for_update()
    res = await db.execute(member_stmt)
    member = res.scalar_one_or_none()
    if not member or not member.is_active:
        raise HTTPException(status_code=400, detail="成員不存在或已被停用")

    pts = record_in.points_awarded
    newly_badges = []

    # 判斷是小孩自主登記 (待審核) 還是家長直接操作 (即時生效)
    if auth_role != "parent":
        # 小孩操作權限限制：小孩僅能申請增加自身點數 (pts > 0)
        if pts <= 0:
            raise HTTPException(status_code=403, detail="小孩僅能申請增加自身點數，不可自訂扣點")
        actor_name = member.name
        record_status = "PENDING"
        # 注意：小孩登記待審核時，不先調增 current_points 與 total_earned_points
    else:
        actor_name = record_in.recorded_by or "Parent"
        record_status = "APPROVED"

        # 家長直接發放/扣點：點數雙軌約束邏輯
        if pts < 0:
            if member.current_points + pts < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"點數不足以扣抵！目前可用點數為 {member.current_points} 點，欲扣除 {-pts} 點",
                )
            member.current_points += pts
        else:
            member.current_points += pts
            member.total_earned_points += pts

    # 2. 快照規則資訊
    rule_snapshot = None
    if record_in.rule_id:
        rule = await db.get(RewardRule, record_in.rule_id)
        if rule:
            rule_snapshot = {
                "id": str(rule.id),
                "target_name": rule.target_name,
                "match_type": rule.match_type,
                "condition_value": rule.condition_value,
                "reward_points": rule.reward_points,
                "description": rule.description,
            }

    # 3. 新增紀錄
    now = datetime.now(timezone.utc)
    kudos = KudosRecord(
        member_id=record_in.member_id,
        rule_id=record_in.rule_id,
        target_name_snapshot=record_in.target_name.strip(),
        condition_snapshot=(record_in.condition_value or "自訂").strip(),
        points_awarded=pts,
        rule_detail_snapshot=rule_snapshot,
        status=record_status,
        note=record_in.note,
        image_url=record_in.image_url,
        reviewed_at=now if record_status == "APPROVED" else None,
        review_note="家長直接登記發放" if record_status == "APPROVED" and auth_role == "parent" else None,
        recorded_by=actor_name,
    )
    db.add(kudos)
    await db.flush()

    # 4. 家長發放時若 pts > 0 評估里程碑勳章
    if record_status == "APPROVED" and pts > 0:
        newly_badges = await evaluate_and_unlock_badges(db, record_in.member_id)

    # 5. 小孩發起申請時，非同步推播 LINE 提醒家長審核
    if record_status == "PENDING" and background_tasks:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        photo_info = "有附照片 📷" if kudos.image_url else "無"
        push_msg = (
            f"🐸 [Frog Kudos 點數申請通知]\n"
            f"成員: {member.name}\n"
            f"目標項目: {kudos.target_name_snapshot}\n"
            f"達成條件: {kudos.condition_snapshot}\n"
            f"申請點數: +{pts} 點\n"
            f"備註: {kudos.note or '無'}\n"
            f"查驗照片: {photo_info}\n"
            f"時間: {time_str}\n"
            f"請家長至系統審核。"
        )
        background_tasks.add_task(send_line_push, push_msg)

    await db.commit()
    await db.refresh(kudos)

    out = KudosRecordOut.model_validate(kudos)
    out.newly_unlocked_badges = newly_badges
    return out

async def list_pending_kudos(
    db: AsyncSession,
    member_id: Optional[uuid.UUID] = None,
) -> List[KudosRecordOut]:
    """查詢所有待家長審核之加點申請 (status='PENDING')"""
    stmt = (
        select(KudosRecord, Member.name)
        .join(Member, KudosRecord.member_id == Member.id)
        .where(KudosRecord.status == "PENDING")
    )
    if member_id:
        stmt = stmt.where(KudosRecord.member_id == member_id)
    stmt = stmt.order_by(KudosRecord.created_at.desc())
    res = await db.execute(stmt)
    records = []
    for k, m_name in res.all():
        out = KudosRecordOut.model_validate(k)
        out.member_name = m_name
        out.target_name = k.target_name_snapshot
        out.condition_value = k.condition_snapshot
        records.append(out)
    return records

async def review_kudos(
    db: AsyncSession,
    kudos_id: uuid.UUID,
    req: KudosReviewIn,
    parent_pin_header: Optional[str] = None,
) -> KudosRecordOut:
    """
    家長審核小孩加點申請
    - 驗證家長安全鎖 PIN 碼
    - 悲觀鎖查詢 kudos 與 member
    - APPROVE: status="APPROVED", 正式發放點數並評估勳章
    - REJECT: status="REJECTED", 註記退回原因
    """
    pin = req.parent_pin or parent_pin_header
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    kudos_stmt = select(KudosRecord).where(KudosRecord.id == kudos_id).with_for_update()
    res = await db.execute(kudos_stmt)
    kudos = res.scalar_one_or_none()
    if not kudos:
        raise HTTPException(status_code=404, detail="查無此點數申請紀錄")

    if kudos.status != "PENDING":
        raise HTTPException(status_code=400, detail="此申請已審核完成，不可重複操作")

    now = datetime.now(timezone.utc)
    newly_badges = []

    if req.action == "APPROVE":
        kudos.status = "APPROVED"
        kudos.reviewed_at = now
        kudos.review_note = req.review_note or "家長已核准發放"

        # 真正加點入成員錢包
        member_stmt = select(Member).where(Member.id == kudos.member_id).with_for_update()
        res_m = await db.execute(member_stmt)
        member = res_m.scalar_one_or_none()
        if not member or not member.is_active:
            raise HTTPException(status_code=400, detail="成員不存在或已被停用")

        pts = kudos.points_awarded
        member.current_points += pts
        member.total_earned_points += pts

        # 評估里程碑勳章
        if pts > 0:
            newly_badges = await evaluate_and_unlock_badges(db, kudos.member_id)

    elif req.action == "REJECT":
        kudos.status = "REJECTED"
        kudos.reviewed_at = now
        kudos.review_note = req.review_note or "家長退回申請"
    else:
        raise HTTPException(status_code=400, detail=f"不支援的審核動作: {req.action}")

    await db.commit()
    await db.refresh(kudos)

    out = KudosRecordOut.model_validate(kudos)
    out.newly_unlocked_badges = newly_badges
    return out

async def get_ledger_history(
    db: AsyncSession,
    member_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> List[LedgerItemOut]:
    """
    查詢家庭綜合存摺流水帳 (FR-6)
    自動合併 kudos_records 與 redemptions 依時間倒序排列
    COMPLETED 兌換記為負數支出，REJECTED 記為 0 點並標註退回原因
    """
    # 查詢 kudos_records
    kudos_stmt = select(KudosRecord)
    if member_id:
        kudos_stmt = kudos_stmt.where(KudosRecord.member_id == member_id)
    kudos_stmt = kudos_stmt.order_by(KudosRecord.created_at.desc()).limit(limit)
    kudos_res = await db.execute(kudos_stmt)
    kudos_list = kudos_res.scalars().all()

    # 查詢 redemptions
    red_stmt = select(Redemption)
    if member_id:
        red_stmt = red_stmt.where(Redemption.member_id == member_id)
    red_stmt = red_stmt.order_by(Redemption.created_at.desc()).limit(limit)
    red_res = await db.execute(red_stmt)
    red_list = red_res.scalars().all()

    items: List[LedgerItemOut] = []

    for k in kudos_list:
        if k.status == "PENDING":
            pts = k.points_awarded
            status_text = f"{k.condition_snapshot} (待家長審核)"
        elif k.status == "REJECTED":
            pts = 0
            status_text = f"已退回 ({k.review_note or '退回'})"
        else:
            pts = k.points_awarded
            status_text = k.condition_snapshot

        items.append(
            LedgerItemOut(
                id=k.id,
                record_type="KUDOS",
                title=k.target_name_snapshot,
                points=pts,
                condition_or_status=status_text,
                status=k.status,
                image_url=k.image_url,
                note=k.note or k.adjustment_note or k.review_note,
                actor=k.recorded_by,
                created_at=k.created_at,
            )
        )

    for r in red_list:
        if r.status == "COMPLETED":
            pts = -r.points_spent
            status_text = "已核銷完成"
        elif r.status == "REJECTED":
            pts = 0
            status_text = f"已退還 ({r.review_note or '退回'})"
        else:
            pts = -r.points_spent
            status_text = "待審核 (已凍結)"

        items.append(
            LedgerItemOut(
                id=r.id,
                record_type="REDEMPTION",
                title=f"兌換: {r.item_title_snapshot}",
                points=pts,
                condition_or_status=status_text,
                status=r.status,
                note=r.review_note,
                actor="Parent" if r.reviewed_at else "系統",
                created_at=r.created_at,
            )
        )

    # 依時間降序排列，取前 limit 筆
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items[:limit]

async def export_ledger_csv(
    db: AsyncSession,
    member_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> str:
    """
    匯出學期成就紀錄與存摺 CSV (FR-17)
    日期過濾採全日包含運算 (< end_date + 1 day)
    """
    # 建立日期過濾條件
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
    if end_date:
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)

    # 取得成員名對照
    members_res = await db.execute(select(Member))
    member_map = {m.id: m.name for m in members_res.scalars().all()}

    # 查詢 kudos_records (僅匯出已核准 APPROVED 紀錄)
    kudos_stmt = select(KudosRecord).where(KudosRecord.status == "APPROVED")
    if member_id:
        kudos_stmt = kudos_stmt.where(KudosRecord.member_id == member_id)
    if start_dt:
        kudos_stmt = kudos_stmt.where(KudosRecord.created_at >= start_dt)
    if end_dt:
        kudos_stmt = kudos_stmt.where(KudosRecord.created_at < end_dt)
    kudos_res = await db.execute(kudos_stmt.order_by(KudosRecord.created_at.asc()))
    kudos_list = kudos_res.scalars().all()

    # 查詢 redemptions
    red_stmt = select(Redemption)
    if member_id:
        red_stmt = red_stmt.where(Redemption.member_id == member_id)
    if start_dt:
        red_stmt = red_stmt.where(Redemption.created_at >= start_dt)
    if end_dt:
        red_stmt = red_stmt.where(Redemption.created_at < end_dt)
    red_res = await db.execute(red_stmt.order_by(Redemption.created_at.asc()))
    red_list = red_res.scalars().all()

    rows = []
    for k in kudos_list:
        rows.append({
            "created_at": k.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "member_name": member_map.get(k.member_id, "未知成員"),
            "record_type": "成就獲得/獎懲",
            "title": k.target_name_snapshot,
            "points": f"+{k.points_awarded}" if k.points_awarded > 0 else str(k.points_awarded),
            "condition": k.condition_snapshot,
            "note": k.note or k.adjustment_note or "",
            "actor": k.recorded_by,
        })

    for r in red_list:
        status_label = "核銷完成" if r.status == "COMPLETED" else ("已退回" if r.status == "REJECTED" else "待審核")
        pts_str = "0" if r.status == "REJECTED" else f"-{r.points_spent}"
        rows.append({
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "member_name": member_map.get(r.member_id, "未知成員"),
            "record_type": "商城兌換",
            "title": f"兌換: {r.item_title_snapshot}",
            "points": pts_str,
            "condition": status_label,
            "note": r.review_note or "",
            "actor": "Parent" if r.reviewed_at else "系統",
        })

    # 依時間升序排列
    rows.sort(key=lambda x: x["created_at"])

    output = io.StringIO()
    # 寫入 UTF-8 BOM 供 Excel 相容中文
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["時間", "成員姓名", "紀錄類型", "項目名稱", "點數異動", "達成條件/狀態", "備註說明", "操作人"])
    for r in rows:
        writer.writerow([
            r["created_at"],
            r["member_name"],
            r["record_type"],
            r["title"],
            r["points"],
            r["condition"],
            r["note"],
            r["actor"],
        ])

    return output.getvalue()

async def preview_batch_adjustment(
    db: AsyncSession,
    preview_in: BatchPreviewIn,
) -> BatchPreviewOut:
    """
    歷史積分批次調整試算預覽 (FR-7)
    採全日包含運算 (< end_date + 1 day)
    """
    start_dt = datetime.combine(preview_in.start_date, time.min).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(preview_in.end_date + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)

    stmt = select(KudosRecord).where(
        KudosRecord.member_id == preview_in.member_id,
        KudosRecord.target_name_snapshot == preview_in.target_name.strip(),
        KudosRecord.status == "APPROVED",
        KudosRecord.created_at >= start_dt,
        KudosRecord.created_at < end_dt,
    ).order_by(KudosRecord.created_at.asc())

    res = await db.execute(stmt)
    records = list(res.scalars().all())

    items: List[BatchPreviewItem] = []
    orig_total = 0
    new_total = 0

    for r in records:
        old_pts = r.points_awarded
        if preview_in.mode == "FIXED":
            new_pts = preview_in.value
            delta = new_pts - old_pts
        else:  # OFFSET
            new_pts = old_pts + preview_in.value
            delta = preview_in.value

        orig_total += old_pts
        new_total += new_pts

        items.append(
            BatchPreviewItem(
                id=r.id,
                target_name=r.target_name_snapshot,
                condition=r.condition_snapshot,
                old_points=old_pts,
                new_points=new_pts,
                delta=delta,
                created_at=r.created_at,
            )
        )

    return BatchPreviewOut(
        affected_count=len(records),
        original_total=orig_total,
        new_total=new_total,
        delta=new_total - orig_total,
        items=items,
    )

async def execute_batch_adjustment(
    db: AsyncSession,
    adjust_in: BatchAdjustIn,
    parent_pin_header: Optional[str] = None,
) -> BatchAdjustOut:
    """
    執行歷史積分批次統一調整 (FR-7, 3.3 演算法)
    - 驗證家長安全鎖 PIN 碼
    - 行級悲觀鎖鎖定成員 SELECT ... FOR UPDATE
    - 日期全日包含過濾 (< end_date + 1 day)
    - 雙軌餘額防負檢查 (current_points + Δ >= 0 且 total_earned_points + Δ >= 0)
    - 批次更新快照紀錄與變更原因
    - 里程碑勳章同步評估 (Δ > 0 時)
    - ACID Transaction 提交
    """
    pin = adjust_in.parent_pin or parent_pin_header
    if not await verify_parent_pin(db, pin):
        raise HTTPException(status_code=403, detail="家長安全鎖 PIN 碼錯誤或未授權")

    # 1. 鎖定成員資料列
    member_stmt = select(Member).where(Member.id == adjust_in.member_id).with_for_update()
    res_m = await db.execute(member_stmt)
    member = res_m.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")

    # 2. 查詢符合條件紀錄
    start_dt = datetime.combine(adjust_in.start_date, time.min).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(adjust_in.end_date + timedelta(days=1), time.min).replace(tzinfo=timezone.utc)

    stmt = select(KudosRecord).where(
        KudosRecord.member_id == adjust_in.member_id,
        KudosRecord.target_name_snapshot == adjust_in.target_name.strip(),
        KudosRecord.status == "APPROVED",
        KudosRecord.created_at >= start_dt,
        KudosRecord.created_at < end_dt,
    )
    res_r = await db.execute(stmt)
    records = list(res_r.scalars().all())

    if not records:
        raise HTTPException(status_code=404, detail="查無符合條件之歷史紀錄")

    # 3. 計算各筆新點數與總變動量 Δ
    total_delta = 0
    now = datetime.now(timezone.utc)

    for r in records:
        old_pts = r.points_awarded
        if adjust_in.mode == "FIXED":
            new_pts = adjust_in.value
            delta = new_pts - old_pts
        else:  # OFFSET
            new_pts = old_pts + adjust_in.value
            delta = adjust_in.value

        total_delta += delta
        r.points_awarded = new_pts
        r.adjustment_note = adjust_in.reason.strip()
        r.updated_at = now

    # 4. 雙軌餘額防負檢查 (不可透支已兌換或導致累計為負數)
    if member.current_points + total_delta < 0:
        raise HTTPException(
            status_code=400,
            detail=f"調降後可用點數不足！變動差額為 {total_delta} 點，成員目前僅餘 {member.current_points} 點 (可能已用於商城兌換)",
        )
    if member.total_earned_points + total_delta < 0:
        raise HTTPException(
            status_code=400,
            detail=f"調降後歷史累計點數將為負數 ({member.total_earned_points + total_delta})，系統拒絕執行",
        )

    # 5. 更新成員餘額
    member.current_points += total_delta
    member.total_earned_points += total_delta

    # 6. 里程碑勳章同步評估 (若 Δ > 0)
    newly_badges = []
    if total_delta > 0:
        newly_badges = await evaluate_and_unlock_badges(db, adjust_in.member_id)

    await db.commit()
    await db.refresh(member)

    return BatchAdjustOut(
        affected_count=len(records),
        total_points_delta=total_delta,
        member_current_points=member.current_points,
        member_total_earned_points=member.total_earned_points,
        newly_unlocked_badges=newly_badges,
    )
