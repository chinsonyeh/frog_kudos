import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException

from app.models.member import Member
from app.models.member_badge import MemberBadge
from app.models.badge import Badge
from app.models.kudos_record import KudosRecord
from app.models.reward_rule import RewardRule
from app.models.category import Category
from app.schemas.badge import MemberBadgeOut, BadgeCreate, BadgeUpdate, BadgeOut

BADGE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "FIRST_100_PTS": {"title": "初出茅廬蛙", "description": "累計獲得 100 點", "icon": "🌟", "target": 100, "reward_points": 25, "is_repeatable": True},
    "PERFECT_SCORE_5": {"title": "百分學霸蛙", "description": "科目滿分達 5 次", "icon": "🏆", "target": 5, "reward_points": 50, "is_repeatable": True},
    "CHORE_MASTER_200": {"title": "家事小達人", "description": "生活常規或家事協助累計獲得 200 點", "icon": "🧹", "target": 200, "reward_points": 50, "is_repeatable": True},
    "MILLIONAIRE_1000": {"title": "點數千元蛙", "description": "累計獲得 1,000 點", "icon": "👑", "target": 1000, "reward_points": 250, "is_repeatable": True},
    "POINTS_5000": {"title": "五千非凡蛙", "description": "累計獲得 5,000 點", "icon": "💎", "target": 5000, "reward_points": 1250, "is_repeatable": True},
    "POINTS_10000": {"title": "萬點榮耀蛙", "description": "累計獲得 10,000 點", "icon": "🎖️", "target": 10000, "reward_points": 2500, "is_repeatable": True},
    "POINTS_20000": {"title": "兩萬破繭蛙", "description": "累計獲得 20,000 點", "icon": "🚀", "target": 20000, "reward_points": 5000, "is_repeatable": True},
    "POINTS_30000": {"title": "三萬卓越蛙", "description": "累計獲得 30,000 點", "icon": "⚡", "target": 30000, "reward_points": 7500, "is_repeatable": True},
    "POINTS_40000": {"title": "四萬巔峰蛙", "description": "累計獲得 40,000 點", "icon": "🔥", "target": 40000, "reward_points": 10000, "is_repeatable": True},
    "POINTS_50000": {"title": "五萬傳奇蛙", "description": "累計獲得 50,000 點", "icon": "🔮", "target": 50000, "reward_points": 12500, "is_repeatable": True},
    "POINTS_60000": {"title": "六萬超神蛙", "description": "累計獲得 60,000 點", "icon": "🌈", "target": 60000, "reward_points": 15000, "is_repeatable": True},
    "POINTS_70000": {"title": "七萬極限蛙", "description": "累計獲得 70,000 點", "icon": "🌠", "target": 70000, "reward_points": 17500, "is_repeatable": True},
    "POINTS_80000": {"title": "八萬無雙蛙", "description": "累計獲得 80,000 點", "icon": "🛡️", "target": 80000, "reward_points": 20000, "is_repeatable": True},
    "POINTS_90000": {"title": "九萬至尊蛙", "description": "累計獲得 90,000 點", "icon": "🔱", "target": 90000, "reward_points": 22500, "is_repeatable": True},
    "POINTS_100000": {"title": "十萬不朽蛙", "description": "累計獲得 100,000 點", "icon": "🪐", "target": 100000, "reward_points": 25000, "is_repeatable": True},
}

async def get_all_badges(db: AsyncSession, active_only: bool = False) -> List[Badge]:
    """取得所有勳章定義清單"""
    stmt = select(Badge)
    if active_only:
        stmt = stmt.where(Badge.is_active == True)
    stmt = stmt.order_by(Badge.sort_order.asc(), Badge.target_value.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def create_badge(db: AsyncSession, badge_in: BadgeCreate) -> Badge:
    """新增勳章定義"""
    key = badge_in.badge_key
    if not key:
        # 自動根據類型與目標生成 key
        key = f"{badge_in.condition_type}_{badge_in.target_value}"
    
    # 檢查 key 是否已存在
    existing = await db.execute(select(Badge).where(Badge.badge_key == key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"勳章代碼 '{key}' 已存在")

    # 若未自訂獎勵點數，預設按門檻數值的 25% 自動試算
    reward_pts = badge_in.reward_points
    if reward_pts is None:
        if badge_in.condition_type in ("TOTAL_POINTS", "CHORE_POINTS"):
            reward_pts = int(round(badge_in.target_value * 0.25))
        else:
            reward_pts = 0

    badge = Badge(
        badge_key=key,
        title=badge_in.title.strip(),
        description=badge_in.description.strip(),
        icon=badge_in.icon.strip() or "🏅",
        condition_type=badge_in.condition_type,
        target_value=badge_in.target_value,
        reward_points=reward_pts,
        is_repeatable=badge_in.is_repeatable,
        sort_order=badge_in.sort_order,
        is_active=badge_in.is_active,
    )
    db.add(badge)
    await db.commit()
    await db.refresh(badge)
    return badge

async def update_badge(db: AsyncSession, badge_id: uuid.UUID, badge_in: BadgeUpdate) -> Badge:
    """更新勳章定義"""
    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="找不到該勳章定義")

    if badge_in.title is not None:
        badge.title = badge_in.title.strip()
    if badge_in.description is not None:
        badge.description = badge_in.description.strip()
    if badge_in.icon is not None:
        badge.icon = badge_in.icon.strip()
    if badge_in.condition_type is not None:
        badge.condition_type = badge_in.condition_type
    if badge_in.target_value is not None:
        badge.target_value = badge_in.target_value
    if badge_in.reward_points is not None:
        badge.reward_points = badge_in.reward_points
    if badge_in.is_repeatable is not None:
        badge.is_repeatable = badge_in.is_repeatable
    if badge_in.sort_order is not None:
        badge.sort_order = badge_in.sort_order
    if badge_in.is_active is not None:
        badge.is_active = badge_in.is_active

    await db.commit()
    await db.refresh(badge)
    return badge

async def delete_badge(db: AsyncSession, badge_id: uuid.UUID) -> Dict[str, Any]:
    """刪除或停用勳章定義"""
    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="找不到該勳章定義")

    # 檢查是否已有成員解鎖此勳章
    unlocked_count_res = await db.execute(
        select(func.count(MemberBadge.id)).where(MemberBadge.badge_key == badge.badge_key)
    )
    unlocked_count = unlocked_count_res.scalar() or 0

    if unlocked_count > 0:
        # 已有成員獲得，轉為停用
        badge.is_active = False
        await db.commit()
        return {"success": True, "action": "DEACTIVATED", "message": f"該勳章已有 {unlocked_count} 位成員解鎖，已自動轉為停用狀態以維護榮譽紀錄"}
    else:
        await db.delete(badge)
        await db.commit()
        return {"success": True, "action": "DELETED", "message": "勳章已徹底刪除"}

async def toggle_member_badge(
    db: AsyncSession, badge_key: str, member_id: uuid.UUID, unlock: Optional[bool] = None
) -> Dict[str, Any]:
    """手動為成員頒發或收回特定勳章"""
    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="找不到該成員")

    badge = (await db.execute(select(Badge).where(Badge.badge_key == badge_key))).scalar_one_or_none()
    if not badge:
        raise HTTPException(status_code=404, detail=f"找不到代碼為 '{badge_key}' 的勳章")

    existing = (
        await db.execute(
            select(MemberBadge).where(
                MemberBadge.member_id == member_id, MemberBadge.badge_key == badge_key
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if existing:
        if unlock is False or unlock is None:
            # 收回
            await db.delete(existing)
            await db.commit()
            return {"success": True, "unlocked": False, "message": f"已收回 {member.name} 的「{badge.title}」勳章（過往已發放之獎勵點數保留）"}
        elif unlock is True and badge.is_repeatable:
            # 家長再次頒發可重複勳章 (+1 次)
            existing.unlocked_count += 1
            existing.last_unlocked_at = now
            existing.last_target_baseline += badge.target_value
            pts_granted = badge.reward_points
            if pts_granted > 0:
                member.current_points += pts_granted
                reward_kudos = KudosRecord(
                    member_id=member_id,
                    rule_id=None,
                    target_name_snapshot=f"🏅 榮譽勳章手動頒發「{badge.title}」特別獎勵 (第 {existing.unlocked_count} 次)",
                    condition_snapshot="家長手動頒發",
                    points_awarded=pts_granted,
                    rule_detail_snapshot={"badge_key": badge_key, "title": badge.title, "reward_points": pts_granted, "unlocked_count": existing.unlocked_count},
                    status="APPROVED",
                    note=f"家長手動頒發榮譽成就勳章「{badge.title}」第 {existing.unlocked_count} 次獲得額外獎勵點數",
                    reviewed_at=now,
                    review_note="家長手動頒發榮譽成就獎勵",
                    recorded_by="家長",
                )
                db.add(reward_kudos)
            await db.commit()
            bonus_hint = f"（額外獲得 +{pts_granted} 點）" if pts_granted > 0 else ""
            return {"success": True, "unlocked": True, "points_awarded": pts_granted, "message": f"已為 {member.name} 再次頒發「{badge.title}」勳章（第 {existing.unlocked_count} 次）！{bonus_hint}"}
        else:
            return {"success": True, "unlocked": True, "message": f"{member.name} 已擁有「{badge.title}」勳章"}
    else:
        if unlock is True or unlock is None:
            # 頒發
            new_mb = MemberBadge(
                member_id=member_id,
                badge_key=badge_key,
                unlocked_count=1,
                unlocked_at=now,
                last_unlocked_at=now,
                last_target_baseline=badge.target_value,
            )
            db.add(new_mb)
            pts_granted = 0
            if badge.reward_points > 0:
                pts_granted = badge.reward_points
                member.current_points += pts_granted
                reward_kudos = KudosRecord(
                    member_id=member_id,
                    rule_id=None,
                    target_name_snapshot=f"🏅 榮譽勳章頒發「{badge.title}」特別獎勵",
                    condition_snapshot="家長手動頒發",
                    points_awarded=pts_granted,
                    rule_detail_snapshot={"badge_key": badge_key, "title": badge.title, "reward_points": pts_granted, "unlocked_count": 1},
                    status="APPROVED",
                    note=f"家長手動頒發榮譽成就勳章「{badge.title}」獲得額外獎勵點數",
                    reviewed_at=now,
                    review_note="家長手動頒發榮譽成就獎勵",
                    recorded_by="家長",
                )
                db.add(reward_kudos)
            await db.commit()
            bonus_hint = f"（額外獲得 +{pts_granted} 點）" if pts_granted > 0 else ""
            return {"success": True, "unlocked": True, "points_awarded": pts_granted, "message": f"已為 {member.name} 頒發「{badge.title}」勳章！{bonus_hint}"}
        else:
            return {"success": True, "unlocked": False, "message": f"{member.name} 尚未擁有「{badge.title}」勳章"}

async def calculate_badge_progress(db: AsyncSession, member: Member, badges: List[Badge]) -> Dict[str, Dict[str, Any]]:
    """計算指定成員當前所有勳章的進度數值與解鎖判定"""
    # 1. 滿分次數統計 (僅採計已核准 APPROVED 紀錄)
    perfect_stmt = select(func.count(KudosRecord.id)).where(
        KudosRecord.member_id == member.id,
        KudosRecord.status == "APPROVED",
        or_(
            KudosRecord.condition_snapshot == "100",
            KudosRecord.condition_snapshot == "100分",
            KudosRecord.condition_snapshot == "滿分",
        ),
    )
    perfect_count = (await db.execute(perfect_stmt)).scalar() or 0

    # 2. 家事/生活常規點數累計 (僅採計已核准 APPROVED 紀錄)
    chore_stmt = (
        select(func.coalesce(func.sum(KudosRecord.points_awarded), 0))
        .outerjoin(RewardRule, KudosRecord.rule_id == RewardRule.id)
        .outerjoin(Category, RewardRule.category_id == Category.id)
        .where(
            KudosRecord.member_id == member.id,
            KudosRecord.status == "APPROVED",
            KudosRecord.points_awarded > 0,
            or_(
                Category.name.in_(["生活常規", "家事協助"]),
                KudosRecord.target_name_snapshot.like("%家事%"),
                KudosRecord.target_name_snapshot.like("%常規%"),
                KudosRecord.target_name_snapshot.like("%房間%"),
                KudosRecord.target_name_snapshot.like("%洗碗%"),
            ),
        )
    )
    chore_points = (await db.execute(chore_stmt)).scalar() or 0

    # 3. 查詢已存在的 member_badges 記錄
    mb_stmt = select(MemberBadge).where(MemberBadge.member_id == member.id)
    mb_result = await db.execute(mb_stmt)
    mb_map = {mb.badge_key: mb for mb in mb_result.scalars().all()}

    results: Dict[str, Dict[str, Any]] = {}
    for b in badges:
        if b.condition_type == "TOTAL_POINTS":
            raw_val = member.total_earned_points
        elif b.condition_type == "PERFECT_SCORE_COUNT":
            raw_val = perfect_count
        elif b.condition_type == "CHORE_POINTS":
            raw_val = chore_points
        else: # CUSTOM
            raw_val = 0

        mb = mb_map.get(b.badge_key)
        target = b.target_value if b.target_value > 0 else 1

        if mb is None:
            # 尚未達成過
            baseline = 0
            cycle_progress = max(0, raw_val - baseline)
            times = cycle_progress // target
            is_met = times >= 1
            display_progress = min(cycle_progress, target)
        else:
            # 過去曾達成過
            if b.is_repeatable:
                baseline = mb.last_target_baseline
                cycle_progress = max(0, raw_val - baseline)
                times = cycle_progress // target
                is_met = times >= 1
                display_progress = cycle_progress % target if is_met else cycle_progress
            else:
                baseline = target
                cycle_progress = raw_val
                times = 0
                is_met = False
                display_progress = target

        results[b.badge_key] = {
            "raw_val": raw_val,
            "baseline": baseline,
            "cycle_progress": cycle_progress,
            "times": times,
            "is_met": is_met,
            "progress": display_progress,
            "target": target,
            "mb": mb,
        }

    return results

async def get_member_badges(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """取得成員所有勳章清單（含進度與解鎖狀態）"""
    member = await db.get(Member, member_id)
    if not member:
        return []

    # 取得資料庫中啟用的勳章清單
    badges = await get_all_badges(db, active_only=True)

    # 計算當前進度與解鎖狀態
    progress_info = await calculate_badge_progress(db, member, badges)

    badges_out = []
    for b in badges:
        key = b.badge_key
        info = progress_info.get(key, {})
        mb = info.get("mb")
        is_unlocked = mb is not None
        unlocked_count = mb.unlocked_count if mb else 0
        unlocked_at = mb.unlocked_at if mb else None
        last_unlocked_at = mb.last_unlocked_at if mb else None
        prog = info.get("progress", 0)

        badges_out.append(
            MemberBadgeOut(
                id=b.id,
                badge_key=key,
                title=b.title,
                description=b.description,
                icon=b.icon,
                condition_type=b.condition_type,
                reward_points=b.reward_points,
                is_repeatable=b.is_repeatable,
                unlocked=is_unlocked,
                unlocked_count=unlocked_count,
                unlocked_at=unlocked_at,
                last_unlocked_at=last_unlocked_at,
                progress=prog,
                target=b.target_value,
            )
        )

    return badges_out

async def evaluate_and_unlock_badges(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """
    評估成員是否有達成新勳章條件。若有達成：
    - 若初次達成：寫入 member_badges 表 (unlocked_count=times, baseline=times*target)
    - 若為可重複達成勳章且再次累積達標：更新 member_badges 表 (unlocked_count+=times, baseline+=times*target)
    - 若該勳章設有額外獎勵點數 (reward_points > 0)，發入可用錢包 (current_points) 並建立 APPROVED 之 kudos_records 存摺明細。
    - 回傳本次新達成之 MemberBadgeOut 清單。
    需在交易內部呼叫。
    """
    member = await db.get(Member, member_id)
    if not member:
        return []

    # 取得啟用中的所有勳章
    badges = await get_all_badges(db, active_only=True)
    if not badges:
        return []

    # 計算條件判定
    progress_info = await calculate_badge_progress(db, member, badges)

    newly_unlocked = []
    now = datetime.now(timezone.utc)

    for b in badges:
        key = b.badge_key
        info = progress_info.get(key)
        if not info or not info.get("is_met"):
            continue

        times = info.get("times", 1)
        if times < 1:
            continue

        mb = info.get("mb")
        bonus_pts = times * b.reward_points

        if mb is None:
            # 初次解鎖
            badge_record = MemberBadge(
                member_id=member_id,
                badge_key=key,
                unlocked_count=times,
                unlocked_at=now,
                last_unlocked_at=now,
                last_target_baseline=times * b.target_value,
            )
            db.add(badge_record)

            # 若設有額外獎勵點數，發入可用錢包並留下正式存摺明細
            if bonus_pts > 0:
                member.current_points += bonus_pts
                times_desc = f" (達成 {times} 次)" if times > 1 else ""
                reward_kudos = KudosRecord(
                    member_id=member_id,
                    rule_id=None,
                    target_name_snapshot=f"🏅 解鎖成就「{b.title}」特別獎勵{times_desc}",
                    condition_snapshot="成就達成",
                    points_awarded=bonus_pts,
                    rule_detail_snapshot={"badge_key": key, "title": b.title, "reward_points": bonus_pts, "unlocked_count": times},
                    status="APPROVED",
                    note=f"達成榮譽成就勳章「{b.title}」{times_desc}獲得額外獎勵點數",
                    reviewed_at=now,
                    review_note="成就系統自動發放",
                    recorded_by="成就系統",
                )
                db.add(reward_kudos)

            newly_unlocked.append(
                MemberBadgeOut(
                    id=b.id,
                    badge_key=key,
                    title=b.title,
                    description=b.description,
                    icon=b.icon,
                    condition_type=b.condition_type,
                    reward_points=bonus_pts,
                    is_repeatable=b.is_repeatable,
                    unlocked=True,
                    unlocked_count=times,
                    unlocked_at=now,
                    last_unlocked_at=now,
                    progress=info["cycle_progress"] % b.target_value,
                    target=b.target_value,
                )
            )

        elif b.is_repeatable:
            # 再次累積達成 (重設後循環累積)
            prev_count = mb.unlocked_count
            mb.unlocked_count += times
            mb.last_unlocked_at = now
            mb.last_target_baseline += times * b.target_value

            if bonus_pts > 0:
                member.current_points += bonus_pts
                new_count = mb.unlocked_count
                times_desc = f" (第 {new_count} 次)" if times == 1 else f" (第 {prev_count + 1}~{new_count} 次)"
                reward_kudos = KudosRecord(
                    member_id=member_id,
                    rule_id=None,
                    target_name_snapshot=f"🏅 達成成就「{b.title}」特別獎勵{times_desc}",
                    condition_snapshot="成就達成",
                    points_awarded=bonus_pts,
                    rule_detail_snapshot={"badge_key": key, "title": b.title, "reward_points": bonus_pts, "unlocked_count": new_count},
                    status="APPROVED",
                    note=f"達成榮譽成就勳章「{b.title}」{times_desc}獲得額外獎勵點數",
                    reviewed_at=now,
                    review_note="成就系統自動發放",
                    recorded_by="成就系統",
                )
                db.add(reward_kudos)

            newly_unlocked.append(
                MemberBadgeOut(
                    id=b.id,
                    badge_key=key,
                    title=b.title,
                    description=b.description,
                    icon=b.icon,
                    condition_type=b.condition_type,
                    reward_points=bonus_pts,
                    is_repeatable=b.is_repeatable,
                    unlocked=True,
                    unlocked_count=mb.unlocked_count,
                    unlocked_at=mb.unlocked_at,
                    last_unlocked_at=now,
                    progress=info["cycle_progress"] % b.target_value,
                    target=b.target_value,
                )
            )

    return newly_unlocked

async def get_pending_badge_notifications(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """
    查詢該成員尚未在前端通知慶祝過之成就勳章 (unlocked_count > last_notified_count)。
    用於小孩用戶登入時彈窗提醒。
    """
    stmt = (
        select(MemberBadge, Badge)
        .join(Badge, MemberBadge.badge_key == Badge.badge_key)
        .where(
            MemberBadge.member_id == member_id,
            MemberBadge.unlocked_count > MemberBadge.last_notified_count,
            Badge.is_active == True,
        )
        .order_by(MemberBadge.last_unlocked_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    pending = []
    for mb, b in rows:
        unnotified_times = mb.unlocked_count - mb.last_notified_count
        bonus_pts = unnotified_times * b.reward_points
        pending.append(
            MemberBadgeOut(
                id=b.id,
                badge_key=b.badge_key,
                title=b.title,
                description=b.description,
                icon=b.icon,
                condition_type=b.condition_type,
                reward_points=bonus_pts,
                is_repeatable=b.is_repeatable,
                unlocked=True,
                unlocked_count=mb.unlocked_count,
                unlocked_at=mb.unlocked_at,
                last_unlocked_at=mb.last_unlocked_at,
                progress=b.target_value,
                target=b.target_value,
            )
        )
    return pending

async def acknowledge_badge_notifications(db: AsyncSession, member_id: uuid.UUID) -> int:
    """
    將該成員所有待通知成就勳章標記為已通知 (last_notified_count = unlocked_count)。
    """
    stmt = select(MemberBadge).where(
        MemberBadge.member_id == member_id,
        MemberBadge.unlocked_count > MemberBadge.last_notified_count,
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    count = len(records)
    for mb in records:
        mb.last_notified_count = mb.unlocked_count
    await db.commit()
    return count
