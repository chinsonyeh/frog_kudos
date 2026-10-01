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
    "FIRST_100_PTS": {"title": "初出茅廬蛙", "description": "累計獲得 100 點", "icon": "🌟", "target": 100},
    "PERFECT_SCORE_5": {"title": "百分學霸蛙", "description": "科目滿分達 5 次", "icon": "🏆", "target": 5},
    "CHORE_MASTER_200": {"title": "家事小達人", "description": "生活常規或家事協助累計獲得 200 點", "icon": "🧹", "target": 200},
    "MILLIONAIRE_1000": {"title": "點數千元蛙", "description": "累計獲得 1,000 點", "icon": "👑", "target": 1000},
    "POINTS_5000": {"title": "五千非凡蛙", "description": "累計獲得 5,000 點", "icon": "💎", "target": 5000},
    "POINTS_10000": {"title": "萬點榮耀蛙", "description": "累計獲得 10,000 點", "icon": "🎖️", "target": 10000},
    "POINTS_20000": {"title": "兩萬破繭蛙", "description": "累計獲得 20,000 點", "icon": "🚀", "target": 20000},
    "POINTS_30000": {"title": "三萬卓越蛙", "description": "累計獲得 30,000 點", "icon": "⚡", "target": 30000},
    "POINTS_40000": {"title": "四萬巔峰蛙", "description": "累計獲得 40,000 點", "icon": "🔥", "target": 40000},
    "POINTS_50000": {"title": "五萬傳奇蛙", "description": "累計獲得 50,000 點", "icon": "🔮", "target": 50000},
    "POINTS_60000": {"title": "六萬超神蛙", "description": "累計獲得 60,000 點", "icon": "🌈", "target": 60000},
    "POINTS_70000": {"title": "七萬極限蛙", "description": "累計獲得 70,000 點", "icon": "🌠", "target": 70000},
    "POINTS_80000": {"title": "八萬無雙蛙", "description": "累計獲得 80,000 點", "icon": "🛡️", "target": 80000},
    "POINTS_90000": {"title": "九萬至尊蛙", "description": "累計獲得 90,000 點", "icon": "🔱", "target": 90000},
    "POINTS_100000": {"title": "十萬不朽蛙", "description": "累計獲得 100,000 點", "icon": "🪐", "target": 100000},
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

    badge = Badge(
        badge_key=key,
        title=badge_in.title.strip(),
        description=badge_in.description.strip(),
        icon=badge_in.icon.strip() or "🏅",
        condition_type=badge_in.condition_type,
        target_value=badge_in.target_value,
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
            return {"success": True, "unlocked": False, "message": f"已收回 {member.name} 的「{badge.title}」勳章"}
        else:
            return {"success": True, "unlocked": True, "message": f"{member.name} 已擁有「{badge.title}」勳章"}
    else:
        if unlock is True or unlock is None:
            # 頒發
            new_mb = MemberBadge(member_id=member_id, badge_key=badge_key, unlocked_at=now)
            db.add(new_mb)
            await db.commit()
            return {"success": True, "unlocked": True, "message": f"已為 {member.name} 頒發「{badge.title}」勳章！"}
        else:
            return {"success": True, "unlocked": False, "message": f"{member.name} 尚未擁有「{badge.title}」勳章"}

async def calculate_badge_progress(db: AsyncSession, member: Member, badges: List[Badge]) -> Dict[str, Dict[str, Any]]:
    """計算指定成員當前所有勳章的進度數值與解鎖判定"""
    # 1. 滿分次數統計
    perfect_stmt = select(func.count(KudosRecord.id)).where(
        KudosRecord.member_id == member.id,
        or_(
            KudosRecord.condition_snapshot == "100",
            KudosRecord.condition_snapshot == "100分",
            KudosRecord.condition_snapshot == "滿分",
        ),
    )
    perfect_count = (await db.execute(perfect_stmt)).scalar() or 0

    # 2. 家事/生活常規點數累計
    chore_stmt = (
        select(func.coalesce(func.sum(KudosRecord.points_awarded), 0))
        .outerjoin(RewardRule, KudosRecord.rule_id == RewardRule.id)
        .outerjoin(Category, RewardRule.category_id == Category.id)
        .where(
            KudosRecord.member_id == member.id,
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

    results: Dict[str, Dict[str, Any]] = {}
    for b in badges:
        if b.condition_type == "TOTAL_POINTS":
            prog = member.total_earned_points
            is_met = prog >= b.target_value
        elif b.condition_type == "PERFECT_SCORE_COUNT":
            prog = perfect_count
            is_met = prog >= b.target_value
        elif b.condition_type == "CHORE_POINTS":
            prog = chore_points
            is_met = prog >= b.target_value
        else: # CUSTOM
            prog = 0
            is_met = False

        results[b.badge_key] = {
            "progress": prog,
            "target": b.target_value,
            "is_met": is_met,
        }

    return results

async def get_member_badges(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """取得成員所有勳章清單（含進度與解鎖狀態）"""
    member = await db.get(Member, member_id)
    if not member:
        return []

    # 取得資料庫中啟用的勳章清單
    badges = await get_all_badges(db, active_only=True)

    # 查詢已儲存之解鎖紀錄
    stmt = select(MemberBadge).where(MemberBadge.member_id == member_id)
    result = await db.execute(stmt)
    unlocked_map = {b.badge_key: b.unlocked_at for b in result.scalars().all()}

    # 計算當前進度
    progress_info = await calculate_badge_progress(db, member, badges)

    badges_out = []
    for b in badges:
        key = b.badge_key
        prog = progress_info.get(key, {"progress": 0, "target": b.target_value, "is_met": False})
        is_unlocked = key in unlocked_map
        badges_out.append(
            MemberBadgeOut(
                id=b.id,
                badge_key=key,
                title=b.title,
                description=b.description,
                icon=b.icon,
                condition_type=b.condition_type,
                unlocked=is_unlocked,
                unlocked_at=unlocked_map.get(key),
                progress=min(prog["progress"], b.target_value) if is_unlocked else prog["progress"],
                target=b.target_value,
            )
        )

    return badges_out

async def evaluate_and_unlock_badges(db: AsyncSession, member_id: uuid.UUID) -> List[MemberBadgeOut]:
    """
    評估成員是否有達成新勳章條件。若有達成且尚未解鎖，寫入 member_badges 表並回傳新解鎖之勳章清單。
    需在交易內部呼叫。
    """
    member = await db.get(Member, member_id)
    if not member:
        return []

    # 取得啟用中的所有勳章
    badges = await get_all_badges(db, active_only=True)
    if not badges:
        return []

    # 查詢已解鎖紀錄
    stmt = select(MemberBadge).where(MemberBadge.member_id == member_id)
    result = await db.execute(stmt)
    existing_keys = {b.badge_key for b in result.scalars().all()}

    # 計算條件判定
    progress_info = await calculate_badge_progress(db, member, badges)

    newly_unlocked = []
    now = datetime.now(timezone.utc)

    for b in badges:
        key = b.badge_key
        info = progress_info.get(key)
        if info and info["is_met"] and key not in existing_keys:
            # 寫入資料庫解鎖紀錄
            badge_record = MemberBadge(
                member_id=member_id,
                badge_key=key,
                unlocked_at=now,
            )
            db.add(badge_record)
            newly_unlocked.append(
                MemberBadgeOut(
                    id=b.id,
                    badge_key=key,
                    title=b.title,
                    description=b.description,
                    icon=b.icon,
                    condition_type=b.condition_type,
                    unlocked=True,
                    unlocked_at=now,
                    progress=b.target_value,
                    target=b.target_value,
                )
            )

    return newly_unlocked
